# JNCA Reference Narrative Notes

This note records the external encrypted-traffic papers used as narrative references for the English SCI/JNCA manuscript. It is not a new experimental claim file; it is a writing and positioning aid.

## Papers Checked

- SoK: Decoding the Enigma of Encrypted Network Traffic Classifiers  
  Source: https://arxiv.org/abs/2503.20093  
  Narrative lesson: start from validity pressure, not from model novelty. The paper foregrounds outdated datasets, shortcut assumptions, feature leakage, and empirical validation of claims.

- ET-BERT: A Contextualized Datagram Representation with Pre-training Transformers for Encrypted Traffic Classification  
  Source: https://arxiv.org/abs/2202.06335  
  Narrative lesson: explain why encrypted traffic needs robust representation learning before introducing the architecture. The story moves from content-invisible traffic to representation difficulty, then to the proposed modeling choice.

- NetMamba: Efficient Network Traffic Classification via Pre-training Unidirectional Mamba  
  Source: https://arxiv.org/abs/2405.11449  
  Narrative lesson: define the practical bottlenecks first, then explain why a state-space architecture is a suitable response. Efficiency is presented as part of the problem definition rather than as an afterthought.

- TrafficFormer: An Efficient Pre-trained Model for Traffic Data  
  Source: https://www.computer.org/csdl/proceedings-article/sp/2025/223600a102/22K50xTq93y  
  Narrative lesson: when introducing a representation model, connect the architecture to what traffic data lacks compared with natural language or images. The model story should explain why traffic needs a tailored representation path, not only report that a modern backbone was used.

- CESNET-TLS-Year22: A Year-Spanning TLS Network Traffic Dataset from Backbone Lines  
  Source: https://www.nature.com/articles/s41597-024-03927-4  
  Narrative lesson: dataset papers in this area earn trust by foregrounding real-network collection, reproducible processing, temporal coverage, and careful boundaries. This supports a more conservative discussion of temporal drift and cross-collection generalization.

- DataZoo: Streamlining Traffic Classification Experiments  
  Source: https://arxiv.org/abs/2310.19568  
  Narrative lesson: reproducibility can be part of the paper story. Standardized data export and task construction should be described as safeguards against accidental differences in preprocessing and evaluation.

- Mobile Encrypted Traffic Classification Using Deep Learning: Experimental Evaluation, Lessons Learned, and Challenges  
  Source: https://ieeexplore.ieee.org/document/8695837  
  Narrative lesson: a mature empirical paper earns trust by defining the traffic visibility, evaluation protocol, baselines, and lessons learned before overstating model novelty. This supports a more explicit controlled-input story.

- DISTILLER: Encrypted Traffic Classification via Multimodal Multitask Deep Learning  
  Source: https://doi.org/10.1016/j.jnca.2021.102985  
  Narrative lesson: a JNCA-style manuscript can position architecture as a response to an operational setting. The story connects available modalities, task design, and deployment relevance instead of treating the model as isolated machinery.

- A Novel Multimodal Deep Learning Framework for Encrypted Traffic Classification  
  Source: https://ieeexplore.ieee.org/document/9913811  
  Narrative lesson: multimodal encrypted-traffic papers often define why each traffic view is useful before showing the fusion model. For the current manuscript, this reinforces the need to explain why only packet size, direction, and timing are used.

- Deep Learning for Encrypted Traffic Classification in the Face of Data Drift  
  Source: https://doi.org/10.1016/j.comnet.2023.109648  
  Narrative lesson: temporal drift and data drift should be treated as central validity boundaries, not minor future-work sentences. This supports a stronger Threats to Validity section around time-aware evaluation.

- The Sweet Danger of Sugar: Debunking Representation Learning Based Network Traffic Classification  
  Source: https://doi.org/10.1145/3718958.3750534  
  Narrative lesson: recent diagnostic work shows why representation-learning claims need shortcut checks and careful split design. This supports framing HSTA as a controlled mechanism study rather than a universal traffic foundation model.

- FlowPic: A Generic Representation for Encrypted Traffic Classification and Applications Identification  
  Source: https://doi.org/10.1109/TNSM.2021.3071441  
  Narrative lesson: strong representation papers explain the representation choice before the network choice. FlowPic's story is useful because it treats traffic-to-representation mapping as the scientific move, not merely as preprocessing.

- A Two-Phase Approach to Fast and Accurate Classification of Encrypted Traffic  
  Source: https://doi.org/10.1109/TNET.2022.3209979  
  Narrative lesson: fast encrypted-traffic papers first define the operational timing pressure, then separate early decisions from later confirmation. This supports describing the first-30-packet setting as an early-decision constraint.

- Classify Traffic Rather Than Flow: Versatile Multi-Flow Encrypted Traffic Classification With Flow Clustering  
  Source: https://doi.org/10.1109/TNSM.2023.3322861  
  Narrative lesson: the traffic unit matters. A paper that shifts from isolated flows to multi-flow behavior makes its unit of analysis explicit, which helps the current manuscript state that HSTA is a single-flow lightweight classifier and not a multi-flow traffic-intelligence system.

- SETA++: Real-Time Scalable Encrypted Traffic Analytics in Multi-Gbps Networks  
  Source: https://doi.org/10.1109/TNSM.2021.3085097  
  Narrative lesson: deployment-oriented papers put throughput, latency, and real-time constraints near the problem statement. This supports keeping efficiency and online feasibility in the story instead of treating them as a minor appendix.

- Rosetta: Enabling Robust TLS Encrypted Traffic Classification in Diverse Network Environments with TCP-Aware Traffic Augmentation  
  Source: https://doi.org/10.1145/3603165.3607437  
  Narrative lesson: robustness papers make environment shift concrete rather than generic. This supports a sharper Threats to Validity section around capture environments, protocol behavior, and augmentation not tested here.

- SAT-Net: A Staggered Attention Network Using Graph Neural Networks for Encrypted Traffic Classification  
  Source: https://doi.org/10.1016/j.jnca.2024.104069  
  Narrative lesson: a recent JNCA paper frames attention and graph modeling as responses to traffic structure. This reinforces that HSTA should explain why attention is placed after sequence transformation, not simply say that attention was added.

## Second-Pass Narrative Lessons

- Strong papers give the reader a contract early: what is observable, what is controlled, what unit is classified, and what claim is intentionally not being made.
- The experimental section should read as an evidence ladder rather than a list of settings: main scores establish recognition quality, ablation tests the mechanism, efficiency tests deployment cost, and transfer tests representation reuse.
- Negative controls strengthen a mechanism story. For HSTA, the no-attention/front-attention/middle-attention variants should be described as tests against the simpler explanation that any attention module would help.
- Cross-protocol transfer should be framed as a stress test of representation reuse, not as proof of protocol-invariant classification.

## Manuscript Adjustments Derived From These Papers

- The Introduction now frames the gap as controlled-input and mechanism-evidence pressure: good accuracy alone is not enough.
- The Introduction now follows a stronger progression inspired by the checked papers: observable-signal scarcity, evaluation validity pressure, then the proposed stage-order mechanism.
- The Introduction now explicitly states the early-flow monitoring setting and describes classification as behavioral inference rather than content recognition.
- The Introduction now makes the 30-packet window read as an early-decision constraint, borrowing the operational framing of fast encrypted-traffic classification work.
- The Introduction now states a clearer reader contract and presents the contribution set as reproducible evaluation, hybrid architecture, mechanism testing, and deployment-relevant evidence.
- The contribution paragraph now states the scope conservatively instead of implying a general-purpose encrypted-traffic foundation model.
- The Experimental Setup now explains the early-flow, closed-set setting and why adapted baselines are interpreted only under the shared 30-packet side-channel input.
- The Experimental Setup now describes the evaluation as an evidence ladder linking recognition quality, mechanism evidence, efficiency cost, and cross-protocol representation reuse.
- The Related Work section now separates multimodal empirical work, representation-learning, efficiency-oriented sequence modeling, graph/attention modeling, multi-flow modeling, shortcut-aware diagnostics, and this paper's constrained first-30-packet side-channel setting.
- The Results section now reads class-scale and transfer findings as evidence about protocol difficulty and representation reuse, not only as score differences.
- The Results section now treats attention-position ablation as a negative control against the simpler claim that any attention module would help.
- The Discussion now reads the results as mechanism evidence rather than a simple leaderboard and states which deployment, multi-flow, feature-rich, and production-scale claims are not proven.
- A dedicated Threats to Validity section now separates controlled-input scope, external validity, construct validity, deployment-measurement limits, temporal drift, capture-environment robustness, and shortcut/split-design limitations.
- The Conclusion now connects accuracy claims with ablation, efficiency, transfer, and deployment-relevant evidence while keeping future claims bounded.

## Boundaries

- No training experiments were rerun.
- No result CSV files were modified.
- The notes above guided wording and structure only; all reported result values still come from the existing generated tables.
- The adapted baselines remain described as adapted structural comparisons under the unified input setting, not as full reproductions of their original pipelines.
