# Intent Recognition SaaS Evaluation

This repo contains evaluation of Autofaq.ai, Cognigy, DialogFlow, Microsoft LUIS and IBM Watson Assistant NLU services.

Data collected at September 2021.

# Setup

Train and test data placed in data/ folder.
Each SaaS reproduce results script placed in jupyter notebook.

HWU64-10 is data from [1] which consists of 64 intents, 10 train sample per intent, and 1076 test examples (data/hwu_small*).
HWU64-30 is also data from [1] which consists of 64 intents, 30 train sample per intent, and 5518 test examples (data/hwu_large*).

# Results

| SaaS name       | F1-macro (HWU64-10)  | Accuracy (HWU64-10)  | F1-macro (HWU64-30)  | Accuracy (HWU64-30)  | Response time (sec.) per query |
| --------------- | -------------------- | -------------------- | -------------------- | -------------------- | ------------------------ |
| Autofaq.ai      | **0.786**            | **0.802**            | **0.858**            | 0.851                | 0.270+-0.035             |
| Cognigy         | 0.771                | 0.776                | 0.829                | 0.842                | 0.590+-0.241           |
| Dialogflow      | 0.649                | 0.640                | 0.754                | 0.756                | 0.273+-0.033             |
| LUIS            | 0.657                | 0.673                | 0.771                | 0.782                | 0.314+-0.053             |
| Watson          | 0.761                | 0.776                | 0.848                | **0.855**            | **0.180+-0.036**         |


# References

1. Liu X. et al. Benchmarking natural language understanding services for building conversational agents //Increasing Naturalness and Flexibility in Spoken Dialogue Interaction. – Springer, Singapore, 2021. – С. 165-183.
2. Dominik Seisser. Benchmarking NLU Engines: A Comparison of Market Leaders https://www.cognigy.com/blog/benchmarking-nlu-engines-comparing-market-leaders, 26 Nov. 2020
3. Qi H. et al. Benchmarking Commercial Intent Detection Services with Practice-Driven Evaluations //Proceedings of the 2021 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies: Industry Papers. – 2021. – С. 304-310.
