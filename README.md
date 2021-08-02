# Open-Information-Extraction-System
中文开放信息抽取系统, open-information-extraction-system, build open-knowledge-graph(SPO, subject-predicate-object) by pyltp(version==3.4.0)


## 码源分析
基于LTP依存句法分析(DP, dependency parsing)的中文开放信息抽取系统(rule-based)。
  - 增加并列关系、左附加关系、右附加关系等(递归实现);
  - 这里的依存句法分析只适合简单短句，过长句子、口语化句子dp效果不好会很影响下游抽取。
  

## 结果展示(部分)
```bash
{
    "ques": "郑州是那个省的",
    "answer": [
        "河南"
    ],
    "desc": "郑州是河南省省会城市，周边有洛阳、开封、新郑、新密、许昌等城市",
    "SPO": [
        [
            "郑州",
            "是",
            "那个省"
        ]
    ]
},
{
    "ques": "格林童话《灰姑娘》中,灰姑娘参加舞会时所做的车是由哪种植物变成的?",
    "answer": [
        "南瓜"
    ],
    "desc": "这时，有一位仙女出现了，帮助她摇身一变成为高贵的千金小姐，并将老鼠变成马夫，南瓜变成马车，又变了一套漂亮的衣服和一双水晶（玻璃）鞋给灰姑娘穿上。",
    "SPO": [
        [
            "灰姑娘",
            "参加",
            "舞会"
        ],
        [
            "灰姑娘",
            "参加",
            "舞会"
        ],
        [
            "做车",
            "是",
            "变成"
        ]
    ]
 },
 {
    "ques": "中国农历的哪个节气有着北方吃饺子、南方吃汤圆的习俗?",
    "answer": [
        "冬至"
    ],
    "desc": "在冬至节，中国北方有冬至日吃饺子的习俗，南方某些地方有冬至日吃汤圆、粉糍粑的习俗，传说在汉朝的医圣张仲景体念家乡乡民在寒冬中工作的辛苦，在冬至那天利用羊肉等祛寒的药材包在面皮中，作成耳朵的样子，给乡民们治病补身，这个药方的名字...",
    "SPO": [
        [
            "中国农历哪个节气",
            "有着",
            "吃饺子习俗"
        ],
        [
            "北方",
            "吃",
            "饺子"
        ],
        [
            "南方",
            "吃",
            "汤圆"
        ]
    ]
}
``` 


# 资源&依赖
- [lemonhu/open-entity-relation-extraction](https://github.com/lemonhu/open-entity-relation-extraction)
- [基于依存句法关系的知识抽取工具](http://openkg.cn/tool/finiancialkg)
- [tim5go/zhopenie](https://github.com/tim5go/zhopenie)
- [HIT-SCIR/ltp](https://github.com/HIT-SCIR/ltp)
- [TJUNLP/COER](https://github.com/TJUNLP/COER)

