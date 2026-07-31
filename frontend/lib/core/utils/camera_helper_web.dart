import 'dart:js' as js;

void forceStopWebcamStreams() {
  try {
    js.context.callMethod('eval', [
      """
      (function() {
        document.querySelectorAll('video').forEach(function(video) {
          if (video.srcObject) {
            var stream = video.srcObject;
            if (typeof stream.getTracks === 'function') {
              stream.getTracks().forEach(function(track) {
                track.stop();
              });
            }
            video.srcObject = null;
          }
        });
      })();
      """
    ]);
  } catch (e) {
    print('Web browser webcam force-kill error: $e');
  }
}
