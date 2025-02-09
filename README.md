<h1 align="center">Scav Case Tracker</h1>

<p align="center">
  This app is a Flask-based tool designed to provide insights into Scav Case runs in the game Escape from Tarkov, offering dynamic statistics such as the most profitable case types, average returns, and item distributions, all visualized using Chart.js for interactive data analysis.<br><br>
  <img src="https://github.com/Throupy/scav-case-tracker/blob/00d1ebe13240f56f200b52b80214ff8fab69233b/app/static/icon.png" alt="Scav Case Tracker Logo" width="275">
</p>
<hr><br>

![image](https://github.com/user-attachments/assets/790d157f-def8-42ee-97e6-de080e959bfb)




# Usage and Setup
```shell
pip install -r requirements.txt
flask run
```

# To Do
- [ ] IMPROVEMENT_1: Put images into S3 / CDN
- [ ] IMPROVEMENT_2: Couple OCR with image recognition

- [ ] FEATURE_1: Some sort of price watcher. Unsure exactly how this will look but definately monitoring historical prices of intel and moonshine. Perhaps include other items that fluctuate (e.g. sugar, GPUs). And items that have increased in value drastically over the last few days (can use tarkov.dev API for this)
- [ ] FEATURE_2: Custom error pages, including specific handling e.g. 404 (case not found).
- [ ] FEATURE_3: Item scraping to be included into the applications startup, while still being controlled from the configuration file.
- [ ] FEATURE_4: Export functionality (CSV, JSON)
- [ ] FEATURE_5: 'Executive Summary' style report

- [X] BUG_1: insights page, when ALL selected, it says Scav Case ID: on the bar hover.
- [X] BUG_2: insights page, when filtering, the titles of all graphs should read the scav case type. only 3 do currently
- [X] BUG_3: `'` in item name on entry page causes JS error and item not added to selected items list.
- [ ] BUG_4: Prices for ammo packs are wrong. tarkov.dev API says that 50 box of 6a1 is worth 480, this is not true. Perhaps "unpack" the box and sell each round individually for a more accurate price?