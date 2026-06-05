# Channel Specifications

## Unity Ads

### openStore function
```javascript
function openStore() {
  try {
    if (window.mraid && typeof window.mraid.open === 'function') {
      window.mraid.open(CLICK_URL);
      return;
    }
  } catch (e) {}
  try {
    if (window.install && typeof window.install === 'function') {
      window.install();
      return;
    }
  } catch (e) {}
  try {
    window.open(CLICK_URL, '_blank', 'noopener');
    return;
  } catch (e) {}
  window.location.href = CLICK_URL;
}
```

### Requirements
- File size: < 5MB
- Single HTML file
- MRAID 2.0 compatible
- No external requests

---

## AppLovin (APL)

### openStore function
```javascript
function openStore() {
  try {
    if (window.mraid && typeof window.mraid.open === 'function') {
      window.mraid.open(CLICK_URL);
      return;
    }
  } catch (e) {}
  try {
    if (window.FbPlayableAd) {
      window.FbPlayableAd.onCTAClick();
      return;
    }
  } catch (e) {}
  try {
    window.open(CLICK_URL, '_blank', 'noopener');
    return;
  } catch (e) {}
  window.location.href = CLICK_URL;
}
```

### Requirements
- File size: < 5MB
- Single HTML file
- MRAID compatible
- FbPlayableAd fallback

---

## Google UAC

### openStore function
```javascript
function openStore() {
  try {
    if (typeof ExitApi !== 'undefined' && ExitApi.exit) {
      ExitApi.exit();
      return;
    }
  } catch (e) {}
  try {
    if (window.mraid && typeof window.mraid.open === 'function') {
      window.mraid.open(CLICK_URL);
      return;
    }
  } catch (e) {}
  try {
    window.open(CLICK_URL, '_blank', 'noopener');
    return;
  } catch (e) {}
  window.location.href = CLICK_URL;
}
```

### Extra head meta
```html
<meta name="ad.size" content="width=320,height=480"/>
```

### Requirements
- File size: < 2MB (strict)
- Single HTML file
- ExitApi integration
- ad.size meta tag required
