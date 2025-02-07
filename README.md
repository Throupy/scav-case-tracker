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
- [X] Entry detail blue badge should display total price, not per item.
- [X] Main blueprint
- [X] Discord bot user role filtering - stop spam
- [ ] Item stats e.g. "most common item" per case.
- [X] Pie chart item distribution (credit: wojteklays)
- [X] Improve entry detail page
- Implement "entry editing"
- [ ] Prices for ammo packs are wrong. tarkov.dev API says that 50 box of 6a1 is worth 480, this is not true. Perhaps "unpack" the box and sell each round individually for a more accurate price?
- [ ] More high-res and better images for entry detail page required
- [X] Trim "most valuable item to date"
- [ ] Couple OCR with image recognition
- [X] Implement edit case functionality
- [ ] Put images into CDN / S3, whatever is free and fastest
- [X] Modify "insights" page to be able to select a sample of cases and have the graphs display. Either by category, or by manually selecting with radio boxes.
- [ ] Export functionality (export all Entries to JSON, CSV, etc)
- [ ] Maybe some sort of 'executive summary' ?
- [ ] Separate DEV and PROD configs