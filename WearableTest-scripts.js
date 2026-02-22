var WearableTest = {};
WearableTest.deckGroup = "[Channel1]";
WearableTest.deckNumber = 1;
WearableTest.scratchEnabled = false;
WearableTest.scratchConfig = {
  intervalsPerRev: 128,
  rpm: 33.333,
  alpha: 1.0 / 8.0,
  beta: 1.0 / 8.0 / 32.0,
  ramp: true
};

WearableTest.scratchHold = function (channel, control, value, status, group) {
  if (value > 0 && !WearableTest.scratchEnabled) {
    engine.scratchEnable(
      WearableTest.deckNumber,
      WearableTest.scratchConfig.intervalsPerRev,
      WearableTest.scratchConfig.rpm,
      WearableTest.scratchConfig.alpha,
      WearableTest.scratchConfig.beta,
      WearableTest.scratchConfig.ramp
    );
    WearableTest.scratchEnabled = true;
  } else if (value === 0 && WearableTest.scratchEnabled) {
    engine.scratchDisable(WearableTest.deckNumber, WearableTest.scratchConfig.ramp);
    WearableTest.scratchEnabled = false;
  }
};

WearableTest.jogTick = function (channel, control, value, status, group) {
  var delta = value - 64;
  if (delta === 0) return;
  if (WearableTest.scratchEnabled) {
    engine.scratchTick(WearableTest.deckNumber, delta);
  } else {
    var amt = delta / 256.0;
    engine.setValue(WearableTest.deckGroup, "jog", amt);
  }
};

WearableTest.playSample = function (channel, control, value, status, group) {
    if (value > 0) {
        engine.setValue("[Sampler1]", "start_play", 1);
    }
};