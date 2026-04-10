# 权威来源列表

本列表用于判断「验证来源 URL」是否在权威名单内。Agent 对每条验证来源 URL 提取**域名**（或主机名），与本列表条目做匹配；匹配方式为：URL 的域名等于列表条目，或以列表条目为后缀（如列表含 `xinhuanet.com` 则 `www.xinhuanet.com` 视为匹配）。若某 URL 的域名在列表中，则该来源视为**权威列表内**；否则视为**列表外**，需由 Agent 评估可靠性并在输出中增加提醒。

以下为示例列表，可按需增删。格式：每行一个域名（不含协议与路径），`#` 后为可选说明。

## 政府 / 官方

- gov.cn
- gov.com
- gov.hk
- gov.tw
- gov.sg
- gov.uk
- gov
- state.gov
- whitehouse.gov

## 主流媒体 / 通讯社（示例）

- xinhuanet.com
- people.com.cn
- cctv.com
- cctv.com.cn
- chinanews.com.cn
- thepaper.cn
- gmw.cn
- cyol.com
- bjd.com.cn
- stcn.com
- cnr.cn
- cri.cn
- news.cn
- xinhua.org

## 事实核查机构（示例）

- factcheck.org
- snopes.com
- politifact.com
- fullfact.org
- afp.com
- reuters.com
- apnews.com
- bbc.com
- bbc.co.uk

## 使用说明

- 列表外来源：Agent 需评估该来源是否可靠（如是否为主流媒体、是否有明确署名与可追溯性），并在输出中**必须**增加提醒：「以下部分来源未列入本技能权威名单，已由 Agent 评估为可参考/需谨慎，请自行判断」或对每条列表外 URL 标注「未在权威列表，请谨慎参考」。
- 全部来源在列表内时，结论可写「已核实/真实」，无需额外提醒。
