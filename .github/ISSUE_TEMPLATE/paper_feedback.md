---
name: 论文阅读反馈
about: 更新你的科研画像与向量数据库
title: "[反馈] "
labels: 'feedback'
assignees: ''
---

**阅读人**：张蕊喜
**论文标题/DOI**：10.1109/CVPR.2023.xxx
**状态**：[x] 精读  [x] 代码复现
**核心启发**：这篇使用了特征级的对抗对齐，对我的域自适应GMM实验有帮助，提高权重。

示例：
**阅读人**：张蕊喜

### 📝 论文 1
**论文标题**：Sessa: Selective State Space Attention
**arXiv ID / DOI**：arXiv:2604.18580
**状态**：[x] 精读  [ ] 代码复现
**核心启发/应用方向**：
> 这篇文章探讨了选择性状态空间模型与注意力机制的结合。在处理高分辨率特征时，这种架构能显著降低计算复杂度。后续可以考虑测试将其引入到我们现有的特征级域自适应网络中，看看是否能替代传统的 Transformer 骨干网络，从而在保持语义分割精度的同时，提升特征对齐阶段的稳定性。

---

### 📝 论文 2
**论文标题**：T-REN: Learning Text-Aligned Region Tokens Improves Dense Vision-Language Alignment and Scalability
**arXiv ID / DOI**：arXiv:2604.18573
**状态**：[x] 精读  [ ] 代码复现
**核心启发/应用方向**：
> 本文主要针对视觉-语言的密集对齐（Dense Alignment）进行了优化。这对于复杂场景的语义分割非常有启发。目前我们跨域任务中的伪标签生成和 GMM 分布匹配主要依赖纯视觉特征，如果能借鉴这种文本对齐的区域 Token 学习机制，或许能引入多模态的先验知识，进一步解决 Target 域长尾类别难以对齐的痛点。
