OPEN_STORE_UNITY = '''  function openStore() {
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
  }'''

OPEN_STORE_APL = '''  function openStore() {
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
  }'''

OPEN_STORE_UAC = '''  function openStore() {
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
  }'''

UAC_META = '<meta name="ad.size" content="width=320,height=480"/>'

CHANNELS = {
    'unity': {
        'name': 'Unity',
        'open_store': OPEN_STORE_UNITY,
        'extra_meta': '',
        'max_size_mb': 5.0,
    },
    'apl': {
        'name': 'AppLovin',
        'open_store': OPEN_STORE_APL,
        'extra_meta': '',
        'max_size_mb': 5.0,
    },
    'uac': {
        'name': 'Google UAC',
        'open_store': OPEN_STORE_UAC,
        'extra_meta': UAC_META,
        'max_size_mb': 5.0,
    },
}
