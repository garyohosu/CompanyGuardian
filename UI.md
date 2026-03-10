# UI Design - CompanyGuardian Dashboard

## 1. コンセプト

**"Living System Monitor"**

CompanyGuardianが日々収集するデータを、単なるテキストレポートではなく、**「生きているシステムの鼓動」**として可視化する。
SF映画のオペレーション画面のような没入感と、一目で状況がわかる実用性を兼ね備えたダッシュボード。

## 2. デザイン方針

- **Visual Style**: Glassmorphism (すりガラス効果) + Neon Glow (サイバーパンク/フューチャリスティック)
- **Animation**:
    - **Data Flow**: 監視プロセスをパーティクルやラインのアニメーションで表現
    - **Status Pulse**: 正常なシステムは穏やかに、異常なシステムは激しく明滅
    - **Micro-interactions**: ホバーやクリックに対するリッチなフィードバック
- **Tech Stack (CDN構成)**:
    - **Core**: React 18 (via unpkg/esm.sh) + JSX (Babel standalone)
    - **Styling**: Tailwind CSS v3 (via CDN script)
    - **Icons**: FontAwesome or Lucide (via CDN)
    - **Animation**: GSAP (GreenSock) or Anime.js
    - **3D/Visuals**: Three.js (背景エフェクト用)
    - **Data Source**: GitHub API or Raw Content (companies.yaml, reports/*.md)

## 3. UI 構造図 (Mermaid)

```mermaid
graph TD
    subgraph "Main Layout (Single Page Application)"
        Header[Header / Global Status Bar]
        
        subgraph "Hero Section (3D Background)"
            SystemHealth[System Health Circle<br/>(Center Piece)]
            LastUpdate[Last Updated Info]
        end

        subgraph "Dashboard Grid (Monitor)"
            direction TB
            
            subgraph "Portal Monitor"
                RootCard[Root Portal Card<br/>(Status/Link/History)]
            end

            subgraph "Virtual Companies"
                Comp1[Auto AI Blog]
                Comp2[MagicBoxAI]
                Comp3[AITecBlog]
                Comp4[...]
            end

            subgraph "Guardian Self-Check"
                GuardianCard[CompanyGuardian Status<br/>(Self-Diagnosis)]
            end
        end

        subgraph "Knowledge Base & Logs"
            TabNav[Tabs: Daily Reports | Incidents | Countermeasures]
            LogViewer[Markdown Viewer Panel]
        end

        Footer[Footer / Copyright]
    end

    %% Data Flow
    Config[companies.yaml] -->|Fetch & Parse| Dashboard Grid
    DailyRep[reports/daily/*.md] -->|Fetch| LogViewer
    Incidents[incidents/*.md] -->|Fetch| LogViewer

    %% Interactions
    RootCard -->|Click| Modal[Detail Modal<br/>(History/Graphs)]
    Comp1 -->|Click| Modal
    GuardianCard -->|Click| Modal
    
    %% Styles
    classDef container fill:#1a1a2e,stroke:#0f3460,color:#fff;
    classDef card fill:rgba(255,255,255,0.1),stroke:#e94560,color:#fff,stroke-dasharray: 5 5;
    classDef monitor fill:#16213e,stroke:#0f3460,color:#4cc9f0;

    class Header,Footer container;
    class RootCard,Comp1,Comp2,Comp3,Comp4,GuardianCard card;
    class SystemHealth,LastUpdate monitor;
```

## 4. UI コンポーネント詳細

### 4.1 System Health (Hero)
- **見た目**: 画面中央上部に配置される巨大な円形または六角形のHUD。
- **機能**: 全システムの総合健全度を%で表示。
- **アニメーション**:
    - 正常時: 青/緑のオーラがゆっくりと回転。
    - 異常発生時: 赤い警告色が点滅し、ノイズエフェクトが走る。

### 4.2 Company Cards
- **見た目**: グリッド状に並ぶカード。各企業のロゴ/名前とステータスアイコンを表示。
- **ステータス表示**:
    - `OK`: 緑の点灯
    - `WARNING`: 黄色の点滅
    - `ERROR`: 赤の点滅 + シェイクアニメーション
- **インタラクション**: カーソルを合わせるとカードが浮き上がり（Z軸移動）、詳細情報（直近のチェック結果）がスライドインする。

### 4.3 Log Viewer
- **見た目**: ターミナル風の黒背景にモノスペースフォント。
- **機能**: GitHub上のMarkdownファイルを非同期で取得し、HTMLとしてレンダリング表示。
- **エフェクト**: テキストが表示される際、タイプライター風に1文字ずつ（あるいは行ごとに）高速で表示される演出。

## 5. 実装ファイル構成案

リポジトリルートの `docs/` または `public/` に配置し、GitHub Pagesで公開することを想定。

```text
docs/
├── index.html       # エントリーポイント (React/Tailwind/GSAP読み込み)
├── styles.css       # カスタムCSS (Glassmorphism, Animations)
├── app.js           # メインロジック (Data Fetching, Rendering)
└── assets/          # 静的リソース
```
