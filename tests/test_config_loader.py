"""
ConfigLoader のテスト

担当クラス: ConfigLoader
責務: companies.yaml を読み込み、Company リストを返す。
      必須フィールドの検証を行う。
"""
import pytest
import textwrap
from unittest.mock import patch, mock_open


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

VALID_YAML = textwrap.dedent("""\
    companies:
      - id: root-portal
        name: Root Portal
        kind: portal
        site: https://garyohosu.github.io/
        enabled: true
        adsense_required: true
        required_adsense_pages:
          - /privacy-policy/
          - /contact/
        checks:
          - site_http
          - top_page_keyword

      - id: auto-ai-blog
        name: Auto AI Blog
        kind: virtual_company
        repo: garyohosu/auto-ai-blog
        site: https://hantani-portfolio.pages.dev/
        enabled: true
        adsense_required: true
        required_adsense_pages:
          - /privacy-policy/
          - /contact/
        checks:
          - github_actions
          - site_http
""")

MINIMAL_YAML = textwrap.dedent("""\
    companies:
      - id: minimal-co
        name: Minimal
        kind: virtual_company
        enabled: true
        checks:
          - site_http
""")

MISSING_ID_YAML = textwrap.dedent("""\
    companies:
      - name: No ID Company
        kind: virtual_company
        enabled: true
        checks:
          - site_http
""")

MISSING_KIND_YAML = textwrap.dedent("""\
    companies:
      - id: no-kind
        name: No Kind
        enabled: true
        checks:
          - site_http
""")

INVALID_YAML = "companies: [unclosed"


# ---------------------------------------------------------------------------
# load() のテスト
# ---------------------------------------------------------------------------

class TestConfigLoaderLoad:

    def test_load_returns_list_of_companies(self):
        """有効な YAML から Company リストが返る"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=VALID_YAML)):
            companies = loader.load("companies/companies.yaml")
        assert isinstance(companies, list)
        assert len(companies) == 2

    def test_load_company_has_required_fields(self):
        """Company オブジェクトが必須フィールド id/name/kind/enabled/checks を持つ"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=VALID_YAML)):
            companies = loader.load("companies/companies.yaml")
        c = companies[0]
        assert c.id == "root-portal"
        assert c.name == "Root Portal"
        assert c.kind.value == "portal"
        assert c.enabled is True
        assert "site_http" in [ck.value for ck in c.checks]

    def test_load_company_optional_site_is_none_when_absent(self):
        """site を持たない Company では site が None になる"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=MINIMAL_YAML)):
            companies = loader.load("companies/companies.yaml")
        assert companies[0].site is None

    def test_load_enabled_false_company_is_included(self):
        """enabled: false の Company もリストに含まれる（フィルタはしない）"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: disabled-co
                name: Disabled
                kind: virtual_company
                enabled: false
                checks:
                  - site_http
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            companies = loader.load("companies/companies.yaml")
        assert len(companies) == 1
        assert companies[0].enabled is False

    def test_load_raises_on_invalid_yaml_syntax(self):
        """YAML 構文エラーで例外が発生する"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=INVALID_YAML)):
            with pytest.raises(Exception):
                loader.load("companies/companies.yaml")

    def test_load_raises_on_file_not_found(self):
        """ファイルが存在しない場合に例外が発生する"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with pytest.raises(FileNotFoundError):
            loader.load("companies/nonexistent.yaml")

    def test_load_required_artifacts_parsed(self):
        """required_artifacts が RequiredArtifact リストとして解析される"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: art-co
                name: Artifact Co
                kind: virtual_company
                enabled: true
                site: https://example.com
                checks:
                  - artifact
                required_artifacts:
                  - type: site_path
                    path: /index.html
                  - type: site_path
                    path: /feed.xml
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            companies = loader.load("companies/companies.yaml")
        artifacts = companies[0].required_artifacts
        assert len(artifacts) == 2
        assert artifacts[0].path == "/index.html"

    def test_load_required_paths_converted_to_artifacts(self):
        """後方互換の required_paths が required_artifacts の site_path に正規化される"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: compat-co
                name: Compat Co
                kind: virtual_company
                enabled: true
                site: https://example.com
                checks:
                  - artifact
                required_paths:
                  - /feed.xml
                  - /index.html
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            companies = loader.load("companies/companies.yaml")
        artifacts = companies[0].required_artifacts
        types = [a.type.value for a in artifacts]
        paths = [a.path for a in artifacts]
        assert all(t == "site_path" for t in types)
        assert "/feed.xml" in paths
        assert "/index.html" in paths

    def test_load_required_paths_and_artifacts_merged_no_duplicate(self):
        """required_paths と required_artifacts が重複排除でマージされる"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: merge-co
                name: Merge Co
                kind: virtual_company
                enabled: true
                site: https://example.com
                checks:
                  - artifact
                required_paths:
                  - /feed.xml
                required_artifacts:
                  - type: site_path
                    path: /feed.xml
                  - type: site_path
                    path: /index.html
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            companies = loader.load("companies/companies.yaml")
        paths = [a.path for a in companies[0].required_artifacts]
        assert paths.count("/feed.xml") == 1

    def test_load_unknown_check_kind_raises_or_warns(self):
        """未知の checks 種別を含む YAML でロードできるか（ロード時は許可、実行時に警告）"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: unknown-co
                name: Unknown
                kind: virtual_company
                enabled: true
                checks:
                  - unknown_check_kind
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            # load は通過し、validate で警告を検出する
            companies = loader.load("companies/companies.yaml")
        assert len(companies) == 1


# ---------------------------------------------------------------------------
# validate() のテスト
# ---------------------------------------------------------------------------

class TestConfigLoaderValidate:

    def test_validate_returns_true_for_valid_companies(self):
        """正常な Company リストは validate が True を返す"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=VALID_YAML)):
            companies = loader.load("companies/companies.yaml")
        assert loader.validate(companies) is True

    def test_validate_returns_false_when_id_missing(self):
        """id がない Company を含む場合は False を返す"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=MISSING_ID_YAML)):
            companies = loader.load("companies/companies.yaml")
        assert loader.validate(companies) is False

    def test_validate_returns_false_when_kind_missing(self):
        """kind がない Company を含む場合は False を返す"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=MISSING_KIND_YAML)):
            companies = loader.load("companies/companies.yaml")
        assert loader.validate(companies) is False

    def test_validate_returns_false_when_duplicate_ids(self):
        """重複した id を持つ Company が存在する場合は False を返す"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: dup
                name: Dup A
                kind: virtual_company
                enabled: true
                checks: [site_http]
              - id: dup
                name: Dup B
                kind: virtual_company
                enabled: true
                checks: [site_http]
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            companies = loader.load("companies/companies.yaml")
        assert loader.validate(companies) is False

    def test_validate_returns_false_when_site_http_check_without_site(self):
        """site_http チェックを持つが site が未設定の Company は False を返す"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: no-site
                name: No Site
                kind: virtual_company
                enabled: true
                checks: [site_http]
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            companies = loader.load("companies/companies.yaml")
        assert loader.validate(companies) is False

    def test_validate_empty_list_returns_true(self):
        """空リストは valid（警告は出てよいが False は返さない）"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        assert loader.validate([]) is True

    def test_validate_returns_false_when_github_actions_check_without_repo(self):
        """github_actions チェックを持つが repo が未設定の Company は False を返す"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: no-repo
                name: No Repo
                kind: virtual_company
                enabled: true
                site: https://example.com
                checks: [github_actions]
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            companies = loader.load("companies/companies.yaml")
        assert loader.validate(companies) is False


# ---------------------------------------------------------------------------
# validate_with_errors() のテスト
# ---------------------------------------------------------------------------

class TestConfigLoaderValidateWithErrors:

    def test_returns_empty_list_for_valid_config(self):
        """正常な設定なら空リストを返す"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: valid-co
                name: Valid Co
                kind: virtual_company
                site: https://example.com
                enabled: true
                checks:
                  - site_http
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            companies = loader.load("companies/companies.yaml")
        errors = loader.validate_with_errors(companies)
        assert errors == []

    def test_detects_duplicate_id(self):
        """重複 ID を検出してエラーメッセージを含む"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: dup-co
                name: Co A
                kind: virtual_company
                enabled: true
                checks: []
              - id: dup-co
                name: Co B
                kind: virtual_company
                enabled: true
                checks: []
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            companies = loader.load("companies/companies.yaml")
        errors = loader.validate_with_errors(companies)
        assert any("重複" in e and "dup-co" in e for e in errors)

    def test_detects_missing_site_for_site_http(self):
        """site_http check があるが site 未設定のエラーを検出"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: no-site
                name: No Site
                kind: virtual_company
                enabled: true
                checks: [site_http]
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            companies = loader.load("companies/companies.yaml")
        errors = loader.validate_with_errors(companies)
        assert any("site" in e.lower() for e in errors)

    def test_detects_missing_repo_for_github_actions(self):
        """github_actions check があるが repo 未設定のエラーを検出"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: no-repo
                name: No Repo
                kind: virtual_company
                site: https://example.com
                enabled: true
                checks: [github_actions]
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            companies = loader.load("companies/companies.yaml")
        errors = loader.validate_with_errors(companies)
        assert any("repo" in e.lower() for e in errors)

    def test_collects_multiple_errors(self):
        """複数エラーをまとめて返す"""
        yaml_data = textwrap.dedent("""\
            companies:
              - id: bad-co
                name: Bad Co
                kind: virtual_company
                enabled: true
                checks: [site_http, github_actions]
        """)
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        with patch("builtins.open", mock_open(read_data=yaml_data)):
            companies = loader.load("companies/companies.yaml")
        errors = loader.validate_with_errors(companies)
        # site_http に site なし + github_actions に repo なし で 2件以上
        assert len(errors) >= 2

    def test_validate_still_returns_bool(self):
        """validate() は後方互換で bool を返す（validate_with_errors 経由）"""
        from guardian.config_loader import ConfigLoader
        loader = ConfigLoader()
        assert loader.validate([]) is True
