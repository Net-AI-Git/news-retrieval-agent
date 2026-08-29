# Retrieval Evaluation

- Timestamp: 2026-08-23T21:09:53+03:00
- Top K: 10
- Question Pass Rate: 54.55%
- Facts Macro Document Precision@10: 73.89%
- Facts Macro Document Recall@10: 87.04%
- Facts Macro MRR@10: 0.9444
- Facts Macro Exact Fact Recall@10: 87.04%
- Corpus Macro Document Precision@10: 69.26%
- Corpus Macro Document Recall@10: 77.78%
- Corpus Macro MRR@10: 0.8426
- Unsupported Correct Empty Rate: 100.00%

## Per Question

### Q01 — PASS

- Retrieval status: ok

#### Facts

- Document Precision@10: 100.00%
- Document Recall@10: 100.00%
- MRR@10: 1.0000
- Exact Fact Recall@10: 100.00%
- Matched URLs: https://www.sportingnews.com/us/nfl/news/lions-packers-live-score-highlights-thursday-night-football/c8af29e6e4202ddb91a41437, https://www.sportingnews.com/us/nfl/news/nfl-standings-2023-playoff-picture-week-13/d51dfe0fbd879c7a1bbadb06
- Missing URLs: None

#### Corpus

- Document Precision@10: 66.67%
- Document Recall@10: 100.00%
- MRR@10: 1.0000
- Matched URLs: https://www.sportingnews.com/us/nfl/news/lions-packers-live-score-highlights-thursday-night-football/c8af29e6e4202ddb91a41437, https://www.sportingnews.com/us/nfl/news/nfl-standings-2023-playoff-picture-week-13/d51dfe0fbd879c7a1bbadb06
- Missing URLs: None

### Q02 — FAIL

- Retrieval status: ok

#### Facts

- Document Precision@10: 100.00%
- Document Recall@10: 100.00%
- MRR@10: 1.0000
- Exact Fact Recall@10: 100.00%
- Matched URLs: https://techcrunch.com/2023/12/18/flipboard-becomes-a-federated-app-with-support-for-activitypub/, https://www.theverge.com/23990974/social-media-2023-fediverse-mastodon-threads-activitypub
- Missing URLs: None

#### Corpus

- Document Precision@10: 100.00%
- Document Recall@10: 50.00%
- MRR@10: 1.0000
- Matched URLs: https://techcrunch.com/2023/12/18/flipboard-becomes-a-federated-app-with-support-for-activitypub/
- Missing URLs: https://www.theverge.com/23990974/social-media-2023-fediverse-mastodon-threads-activitypub

### Q03 — FAIL

- Retrieval status: ok

#### Facts

- Document Precision@10: 50.00%
- Document Recall@10: 100.00%
- MRR@10: 0.5000
- Exact Fact Recall@10: 100.00%
- Matched URLs: https://fortune.com/crypto/2023/10/04/sam-bankman-fried-lawyers-opening-statements-witnesses-marc-antoine-julliard-adam-yedidia-ftx-commodities-trader-developer/, https://techcrunch.com/2023/10/06/sbf-trial-the-latest-updates-from-the-ftx-collapses-courtroom-drama/, https://techcrunch.com/2023/10/07/sam-altman-backs-a-teens-startup-google-unveils-the-pixel-8-and-tiktok-tests-an-ad-free-tier/
- Missing URLs: None

#### Corpus

- Document Precision@10: 20.00%
- Document Recall@10: 33.33%
- MRR@10: 1.0000
- Matched URLs: https://techcrunch.com/2023/10/06/sbf-trial-the-latest-updates-from-the-ftx-collapses-courtroom-drama/
- Missing URLs: https://fortune.com/crypto/2023/10/04/sam-bankman-fried-lawyers-opening-statements-witnesses-marc-antoine-julliard-adam-yedidia-ftx-commodities-trader-developer/, https://techcrunch.com/2023/10/07/sam-altman-backs-a-teens-startup-google-unveils-the-pixel-8-and-tiktok-tests-an-ad-free-tier/

### Q04 — PASS

- Retrieval status: empty
- Correct Empty: True

### Q05 — FAIL

- Retrieval status: ok

#### Facts

- Document Precision@10: 33.33%
- Document Recall@10: 33.33%
- MRR@10: 1.0000
- Exact Fact Recall@10: 33.33%
- Matched URLs: https://techcrunch.com/2023/12/07/early-impressions-of-googles-gemini-arent-great/
- Missing URLs: https://techcrunch.com/2023/12/15/news-publisher-files-class-action-antitrust-suit-against-google-citing-ais-harms-to-their-bottom-line/, https://www.theage.com.au/technology/is-google-search-better-than-the-rest-and-is-that-fair-20231012-p5ebsk.html?ref=rss&utm_medium=rss&utm_source=rss_technology

#### Corpus

- Document Precision@10: 66.67%
- Document Recall@10: 66.67%
- MRR@10: 1.0000
- Matched URLs: https://techcrunch.com/2023/12/07/early-impressions-of-googles-gemini-arent-great/, https://techcrunch.com/2023/12/15/news-publisher-files-class-action-antitrust-suit-against-google-citing-ais-harms-to-their-bottom-line/
- Missing URLs: https://www.theage.com.au/technology/is-google-search-better-than-the-rest-and-is-that-fair-20231012-p5ebsk.html?ref=rss&utm_medium=rss&utm_source=rss_technology

### Q06 — PASS

- Retrieval status: ok

#### Facts

- Document Precision@10: 100.00%
- Document Recall@10: 100.00%
- MRR@10: 1.0000
- Exact Fact Recall@10: 100.00%
- Matched URLs: https://www.theage.com.au/culture/books/author-melissa-lucashenko-on-playing-with-black-and-white-binaries-20230919-p5e5uy.html?ref=rss&utm_medium=rss&utm_source=rss_culture, https://www.theguardian.com/artanddesign/2023/oct/17/i-see-myself-as-a-royal-artist-vincent-namatjira-on-colonialism-satire-and-his-great-grandfathers-legacy
- Missing URLs: None

#### Corpus

- Document Precision@10: 100.00%
- Document Recall@10: 100.00%
- MRR@10: 1.0000
- Matched URLs: https://www.theage.com.au/culture/books/author-melissa-lucashenko-on-playing-with-black-and-white-binaries-20230919-p5e5uy.html?ref=rss&utm_medium=rss&utm_source=rss_culture, https://www.theguardian.com/artanddesign/2023/oct/17/i-see-myself-as-a-royal-artist-vincent-namatjira-on-colonialism-satire-and-his-great-grandfathers-legacy
- Missing URLs: None

### Q07 — PASS

- Retrieval status: ok

#### Facts

- Document Precision@10: 75.00%
- Document Recall@10: 100.00%
- MRR@10: 1.0000
- Exact Fact Recall@10: 100.00%
- Matched URLs: https://techcrunch.com/2023/09/28/chatgpt-everything-to-know-about-the-ai-chatbot/, https://techcrunch.com/2023/11/30/one-year-later-chatgpt-is-still-alive-and-kicking/, https://www.engadget.com/how-openais-chatgpt-has-changed-the-world-in-just-a-year-140050053.html?src=rss
- Missing URLs: None

#### Corpus

- Document Precision@10: 100.00%
- Document Recall@10: 100.00%
- MRR@10: 1.0000
- Matched URLs: https://techcrunch.com/2023/09/28/chatgpt-everything-to-know-about-the-ai-chatbot/, https://techcrunch.com/2023/11/30/one-year-later-chatgpt-is-still-alive-and-kicking/, https://www.engadget.com/how-openais-chatgpt-has-changed-the-world-in-just-a-year-140050053.html?src=rss
- Missing URLs: None

### Q08 — FAIL

- Retrieval status: ok

#### Facts

- Document Precision@10: 100.00%
- Document Recall@10: 50.00%
- MRR@10: 1.0000
- Exact Fact Recall@10: 50.00%
- Matched URLs: https://www.independent.co.uk/travel/skiing/best-luxury-ski-resorts-b2427066.html
- Missing URLs: https://www.independent.co.uk/travel/skiing/best-ski-holidays-canada-b2432416.html

#### Corpus

- Document Precision@10: 100.00%
- Document Recall@10: 100.00%
- MRR@10: 1.0000
- Matched URLs: https://www.independent.co.uk/travel/skiing/best-luxury-ski-resorts-b2427066.html, https://www.independent.co.uk/travel/skiing/best-ski-holidays-canada-b2432416.html
- Missing URLs: None

### Q09 — PASS

- Retrieval status: empty
- Correct Empty: True

### Q10 — FAIL

- Retrieval status: ok

#### Facts

- Document Precision@10: 40.00%
- Document Recall@10: 100.00%
- MRR@10: 1.0000
- Exact Fact Recall@10: 100.00%
- Matched URLs: https://techcrunch.com/2023/09/28/chatgpt-everything-to-know-about-the-ai-chatbot/, https://www.theage.com.au/business/entrepreneurship/how-ego-and-fear-fuelled-the-rise-of-artificial-intelligence-20231205-p5ep7j.html?ref=rss&utm_medium=rss&utm_source=rss_business
- Missing URLs: None

#### Corpus

- Document Precision@10: 20.00%
- Document Recall@10: 50.00%
- MRR@10: 0.2500
- Matched URLs: https://techcrunch.com/2023/09/28/chatgpt-everything-to-know-about-the-ai-chatbot/
- Missing URLs: https://www.theage.com.au/business/entrepreneurship/how-ego-and-fear-fuelled-the-rise-of-artificial-intelligence-20231205-p5ep7j.html?ref=rss&utm_medium=rss&utm_source=rss_business

### Q11 — PASS

- Retrieval status: ok

#### Facts

- Document Precision@10: 66.67%
- Document Recall@10: 100.00%
- MRR@10: 1.0000
- Exact Fact Recall@10: 100.00%
- Matched URLs: https://techcrunch.com/2023/11/30/one-year-later-chatgpt-is-still-alive-and-kicking/, https://techcrunch.com/2023/12/09/google-fakes-an-ai-demo-grand-theft-auto-vi-goes-viral-and-spotify-cuts-jobs/
- Missing URLs: None

#### Corpus

- Document Precision@10: 50.00%
- Document Recall@10: 100.00%
- MRR@10: 0.3333
- Matched URLs: https://techcrunch.com/2023/11/30/one-year-later-chatgpt-is-still-alive-and-kicking/, https://techcrunch.com/2023/12/09/google-fakes-an-ai-demo-grand-theft-auto-vi-goes-viral-and-spotify-cuts-jobs/
- Missing URLs: None
