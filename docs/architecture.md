# MVIF-Net 模型结构图

> 本文件以模型流程图为准。模型结构发生任何变化时，必须同步更新本文件，确保图示与代码一致。

## 正式版：MVIF-Net

```mermaid
flowchart LR
    IN["输入流量 X<br/>[B, 30, 3]<br/>包长 · 方向 · 包间隔"] --> MASK[有效包掩码]
    IN --> XVALID[根据有效掩码将填充包置零]
    MASK --> XVALID

    subgraph M[时序视图：Mamba]
        M0[Linear<br/>3 → 256]
        M1[LayerNorm → Mamba → Dropout<br/>Mamba Block 1；无残差]
        M2[LayerNorm → Mamba → Dropout<br/>Mamba Block 2；无残差]
        MN[时序输出 LayerNorm]
        MP[共享包位置编码<br/>+ Mamba 类型编码]
        MT["30 个 Token<br/>[B, 30, 256]"]
        M0 --> M1 --> M2 --> MN --> MP --> MT
    end

    subgraph G[关系视图：Packet Graph]
        G0[Linear<br/>3 → 256；得到 h₀]
        GA[基于原始包特征构图<br/>自环/相邻边 + 非局部距离 Top-k，k=4]
        G1[图消息块 G1<br/>LayerNorm → 局部/相似邻接消息 → GELU]
        GR{{G1 输出 + αg × h₀<br/>唯一图分支残差<br/>αg 可学习：初始 0.1，范围 (0, 0.5)}}
        G2[图消息块 G2<br/>LayerNorm → 局部/相似邻接消息 → GELU]
        GN[图分支输出 LayerNorm]
        GP[共享包位置编码<br/>+ Graph 类型编码]
        GT["30 个 Token<br/>[B, 30, 256]"]
        G0 --> G1 --> GR --> G2 --> GN --> GP --> GT
        MASK -. 构图掩码 .-> GA
        GA -. 邻接矩阵 .-> G1
        GA -. 邻接矩阵 .-> G2
        G0 -. αg × h₀ .-> GR
    end

    subgraph D[频域视图：DFT-CNN]
        D0[沿 30 包序列做 rFFT]
        D1[16 个频点 × 6 通道<br/>实部 3 + 虚部 3]
        D2[LayerNorm]
        D3[Conv 1×1 投影<br/>6 → 256；得到 f₀]
        D4[Conv k=1<br/>BatchNorm → GELU → Dropout]
        DR{{k=1 输出 + αd × f₀<br/>唯一 DFT 分支残差<br/>αd 可学习：初始 0.1，范围 (0, 0.5)}}
        D5[Conv k=3<br/>BatchNorm → GELU → Dropout]
        DN[DFT 分支输出 LayerNorm]
        DP[频率位置编码<br/>+ DFT 类型编码]
        DT["16 个 Token<br/>[B, 16, 256]"]
        D0 --> D1 --> D2 --> D3 --> D4 --> DR --> D5 --> DN --> DP --> DT
        D3 -. αd × f₀ .-> DR
    end

    XVALID --> M0
    XVALID --> G0
    XVALID --> GA
    XVALID --> D0

    MT --> MNF[Mamba 分支归一化]
    GT --> GNF[Graph 分支归一化]
    DT --> DNF[DFT 分支归一化]
    MNF --> MS[Mamba 有效 Token<br/>masked mean]
    GNF --> GS[Graph 有效 Token<br/>masked mean]
    DNF --> DS[DFT Token<br/>masked mean]
    MASK -. 有效包位置 .-> MS
    MASK -. 有效包位置 .-> GS
    MS --> JOIN["拼接三个分支摘要<br/>[B, 768]"]
    GS --> JOIN
    DS --> JOIN
    JOIN --> GATE[门控 MLP<br/>768 → 128 → 3 → Softmax]
    GATE --> WEIGHT[得到 [gM, gG, gD]<br/>对应分支 Token 分别乘 3g]
    MNF --> WEIGHT
    GNF --> WEIGHT
    DNF --> WEIGHT
    WEIGHT --> CAT["拼接加权 Token<br/>30 + 30 + 16 = 76<br/>[B, 76, 256]"]
    CAT --> TF[Token Fusion<br/>Linear → GELU → Dropout]
    TF --> ATTN[单层 4 头 SDPA 注意力<br/>Key Padding Mask]
    MASK --> KPM[拼接三路有效 Token Mask<br/>30 + 30 + 16]
    KPM -. Key Padding Mask .-> ATTN
    ATTN --> AR{{注意力残差<br/>x₁ = x + Attention(LN(x))}}
    AR --> FFN[前馈网络 FFN<br/>Linear → GELU → Linear]
    FFN --> FR{{FFN 残差<br/>x₂ = x₁ + FFN(LN(x₁))}}
    FR --> OUTN[LayerNorm]
    OUTN --> POOL[全部有效 Token<br/>一次 Global Masked Mean]
    KPM -. 有效位置 .-> POOL
    POOL --> HEAD[Linear<br/>256 → C]
    HEAD --> CLS[分类输出<br/>C = 61：开放集<br/>C = 60：闭集]

    classDef input fill:#E8F1FB,stroke:#2E6FAD,stroke-width:1.5px,color:#17212B;
    classDef branch fill:#F7F7F7,stroke:#6B7280,stroke-width:1.2px,color:#17212B;
    classDef residual fill:#FFF1D6,stroke:#C47B13,stroke-width:1.5px,color:#17212B;
    classDef fusion fill:#EAF6EE,stroke:#398A58,stroke-width:1.5px,color:#17212B;
    classDef output fill:#F3EAF8,stroke:#76539A,stroke-width:1.5px,color:#17212B;
    class IN,MASK input;
    class M0,M1,M2,MN,MP,MT,G0,GA,G1,G2,GN,GP,GT,D0,D1,D2,D3,D4,D5,DN,DP,DT branch;
    class GR,DR,AR,FR residual;
    class MNF,GNF,DNF,MS,GS,DS,JOIN,GATE,WEIGHT,CAT,TF,ATTN,FFN,OUTN,POOL fusion;
    class HEAD,CLS output;
```

## Bi-Mamba+ 单种子实验变体

```mermaid
flowchart LR
    BIN["输入流量 X<br/>[B, 30, 3]"] --> BMASK[有效包掩码]
    BIN --> BX[根据有效掩码将填充包置零]
    BMASK --> BX
    BX --> BM0[Linear<br/>3 → 256]

    subgraph BMT[双向 Mamba+：单层编码器]
        FWD[正向 Mamba+ Mixer]
        FADD{{正向 Add & Norm<br/>x + Mixer(x) → LayerNorm}}
        BWD[反向 Mamba+ Mixer<br/>按有效包长度反转输入]
        BADD{{反向 Add & Norm<br/>xʳ + Mixer(xʳ) → LayerNorm}}
        MERGE[反向结果还原顺序<br/>正向 + 反向]
        BFFN[FFN]
        BRES{{FFN Add & Norm}}
        FWD --> FADD
        BWD --> BADD
        FADD --> MERGE
        BADD --> MERGE
        MERGE --> BFFN --> BRES
    end
    BM0 --> FWD
    BM0 --> BWD
    BRES --> BMTOK[加包位置编码 + 类型编码<br/>30 个 Mamba Token]

    subgraph BDG[动态图视图]
        BG0[Linear<br/>3 → 256]
        BG1[动态图消息块 G1<br/>局部顺序边 + 隐藏特征相似边]
        BG2[动态图消息块 G2<br/>按更新后特征重算相似边]
        BGN[图分支输出 LayerNorm]
        BG0 --> BG1 --> BG2 --> BGN
    end
    BX --> BG0
    BGN --> BGTOK[加包位置编码 + 类型编码<br/>30 个 Graph Token<br/>无图残差]

    subgraph BDF[可学习 DFT-CNN]
        BD0[沿包序列 rFFT<br/>乘可学习复数频响]
        BD1[16 个频点<br/>实部 / 虚部共 6 通道]
        BD2[LayerNorm + Conv 1×1<br/>得到 f₀]
        BD3[Conv k=1<br/>BatchNorm → GELU → Dropout]
    BDR{{k=1 输出 + αd × f₀<br/>αd 初始 0.1，范围 (0, 0.5)}}
        BD4[Conv k=3<br/>BatchNorm → GELU → Dropout]
        BDN[DFT 分支输出 LayerNorm]
        BD0 --> BD1 --> BD2 --> BD3 --> BDR --> BD4 --> BDN
        BD2 -. αd × f₀ .-> BDR
    end
    BX --> BD0
    BDN --> BDTOK[加频率位置编码 + 类型编码<br/>16 个 DFT Token]

    BMTOK --> BMN[Mamba 分支归一化：Identity<br/>Bi-Mamba+ 内部已完成 Add & Norm]
    BGTOK --> BGNORM[Graph 分支 LayerNorm]
    BDTOK --> BDNORM[DFT 分支 LayerNorm]
    BMN --> BMS[Mamba masked mean]
    BGNORM --> BGS[Graph masked mean]
    BDNORM --> BDS[DFT masked mean]
    BMS --> BJOIN["拼接分支摘要<br/>[B, 768]"]
    BGS --> BJOIN
    BDS --> BJOIN
    BMASK -. Mamba / Graph 有效位置 .-> BMS
    BMASK -. Mamba / Graph 有效位置 .-> BGS
    BJOIN --> BGATE[门控 MLP<br/>768 → 128 → 3 → Softmax]
    BGATE --> BWEIGHT["[gM, gG, gD]<br/>各路 Token 乘 3g"]
    BMN --> BWEIGHT
    BGNORM --> BWEIGHT
    BDNORM --> BWEIGHT
    BWEIGHT --> BCAT["拼接 76 个 Token<br/>[B, 76, 256]"]
    BCAT --> BTF[Token Fusion]
    BTF --> BAT[单层 SDPA 注意力<br/>Key Padding Mask]
    BMASK --> BKPM[拼接三路有效 Token Mask<br/>30 + 30 + 16]
    BKPM -. Key Padding Mask .-> BAT
    BAT --> BAR{{注意力残差<br/>x₁ = x + Attention(LN(x))}}
    BAR --> BFFN2[前馈网络 FFN]
    BFFN2 --> BFR{{FFN 残差<br/>x₂ = x₁ + FFN(LN(x₁))}}
    BFR --> BNORM[LayerNorm]
    BNORM --> BPOOL[全部有效 Token<br/>Global Masked Mean]
    BKPM -. 有效位置 .-> BPOOL
    BPOOL --> BHEAD[Linear 256 → C<br/>61 类开放集 / 60 类闭集]

    classDef input fill:#E8F1FB,stroke:#2E6FAD,stroke-width:1.5px,color:#17212B;
    classDef branch fill:#F7F7F7,stroke:#6B7280,stroke-width:1.2px,color:#17212B;
    classDef residual fill:#FFF1D6,stroke:#C47B13,stroke-width:1.5px,color:#17212B;
    classDef fusion fill:#EAF6EE,stroke:#398A58,stroke-width:1.5px,color:#17212B;
    classDef output fill:#F3EAF8,stroke:#76539A,stroke-width:1.5px,color:#17212B;
    class BIN,BM0 input;
    class FWD,BWD,MERGE,BFFN,BG0,BG1,BG2,BGN,BD0,BD1,BD2,BD3,BD4,BDN,BMTOK,BGTOK,BDTOK,BFFN2 branch;
    class FADD,BADD,BRES,BDR,BAR,BFR residual;
    class BMN,BGNORM,BDNORM,BMS,BGS,BDS,BJOIN,BGATE,BWEIGHT,BCAT,BTF,BAT,BNORM,BPOOL fusion;
    class BHEAD output;
```

## 张量尺寸

```text
输入流量                      [B, 30, 3]
Mamba / 图分支                 [B, 30, 256] → 各 30 个 Token
DFT-CNN 分支                  [B, 16, 256] → 16 个 Token
三路拼接                      [B, 76, 256]
全局 masked mean               [B, 256]
分类输出                      [B, 61] 或 [B, 60]
```

## 结构标记

```text
αg、αd        独立可学习的有界残差倍率，初始化 0.1，范围 (0, 0.5)
× 3g          分支门控权重作用于每一路 Token，发生在三路拼接之前
有效包掩码    用于图构建、分支摘要、注意力 key padding 与最终全局池化
```
