# 知识锚点表

> 目的：帮助 Agent 在路由、规划或实现前加载合适知识。
> 这是轻量映射表，不是搜索索引。锚点命中时，读取对应 lesson，并向 `knowledge-usage-ledger.jsonl` 追加使用事件。

## 锚点规则

- 按语义匹配，不按精确措辞匹配。
- 除非用户明确要求更广泛研究，否则最多加载 3 条映射知识。
- 如果命中区域风险较高但没有对应知识，不要编造规则，记录 learn 候选。
- 如果条目只是弱相关，可记录 `event_type: "loaded"`，但除非真正应用，否则不作为升级证据。

## 映射

| 锚点 | 加载 | 阶段 | 原因 |
|------|------|------|------|
| DTO / payload shape / third-party payload / frontend-backend contract / double-encoded JSON | `kf-20260607-contract-before-ui` | routing, planning | 契约消费者不应在 owner-layer 诊断前吸收脏 provider payload。 |
| UI before schema / editor workflow / update API / render boundary | `kf-20260607-contract-before-ui` | planning | UI 应消费稳定契约，而不是绑定内部实现细节。 |
| prompt quality unstable / layout hallucination / generated SVG or HTML | `kf-20260601-prompt-constraints`, `kf-20260601-prompt-complexity-splitting` | planning | 生成结构化输出需要约束，并降低单轮复杂度。 |
| rule file referenced / prompt file referenced / skill references not taking effect | `kf-20260601-prompt-runtime-loading` | routing, implementation | 被引用文件必须显式读取进上下文。 |
| flex column / preview panel / iframe wrapper / height 100% / min-height | `kf-20260609-flex-min-height` | implementation | Flex 子元素通常需要 `min-height: 0` 才能正确收缩。 |
| scroll container / overflow hidden / scrollHeight equals clientHeight / clipped cards | `kf-20260609-scroll-flex-shrink` | implementation | 滚动容器子元素应保持自然高度，避免意外 shrink。 |
| React ref / useEffect deps / event listener not attached / third-party DOM init | `kf-20260622-react-ref-deps` | implementation | `ref.current` 变化不会通过稳定 ref 对象触发 effects。 |
| high precision extraction / interface list / scope check / spec compliance / >95% accuracy | `kf-20260630-deterministic-gate` | planning, verification | 高精度 Gate 应先由确定性脚本处理，再进入 LLM review。 |

## 添加锚点

只有满足以下条件时才添加锚点：

- 映射知识已有稳定 `ID`；
- 触发条件足够具体，不会导致过宽加载；
- 原因说明该知识如何改变决策。

如果某个锚点反复触发但映射条目没有帮助，记录 `challenged` 事件，并在 session 收口时建议更新锚点表。
