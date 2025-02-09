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
- [X] ScavCase detail blue badge should display total price, not per item.
- [X] Main blueprint
- [X] Discord bot user role filtering - stop spam
- [ ] Item stats e.g. "most common item" per case.
- [X] Pie chart item distribution (credit: wojteklays)
- [X] Improve scav case detail page
- Implement "scav case editing"
- [ ] Prices for ammo packs are wrong. tarkov.dev API says that 50 box of 6a1 is worth 480, this is not true. Perhaps "unpack" the box and sell each round individually for a more accurate price?
- [ ] More high-res and better images for scav case detail page required
- [X] Trim "most valuable item to date"
- [ ] Couple OCR with image recognition
- [X] Implement edit case functionality
- [ ] Put images into CDN / S3, whatever is free and fastest
- [X] Modify "insights" page to be able to select a sample of cases and have the graphs display. Either by category, or by manually selecting with radio boxes.
- [ ] Export functionality (export all Entries to JSON, CSV, etc)
- [ ] Maybe some sort of 'executive summary' ?
- [X] Separate DEV and PROD configs
- [ ] BUG_1: insights page, when ALL selected, it says Scav Case ID: on the bar hover.
- [X] BUG_2: insights page, when filtering, the titles of all graphs should read the scav case type. only 3 do currently
- [ ] FEATURE_1: Some sort of price watcher. Unsure exactly how this will look but definately monitoring historical prices of intel and moonshine. Perhaps include other items that fluctuate (e.g. sugar, GPUs). And items that have increased in value drastically over the last few days (can use tarkov.dev API for this)
- [ ] Item scraping via config variable integrate into create_app()
- [ ] Refactor codebase (entire)
- [ ] BUG_3: `'` in item name on entry page causes JS error and item not added to selected items list.
