import 'camera_helper_stub.dart'
    if (dart.library.js) 'camera_helper_web.dart' as helper;

void forceStopWebcamStreams() {
  helper.forceStopWebcamStreams();
}
