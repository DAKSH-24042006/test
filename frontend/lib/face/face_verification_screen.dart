import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:camera/camera.dart';
import 'package:go_router/go_router.dart';
import 'package:google_mlkit_face_detection/google_mlkit_face_detection.dart';
import 'package:smart_attendance/core/providers/face_provider.dart';
import 'package:smart_attendance/core/providers/student_provider.dart';
import 'package:smart_attendance/core/theme/app_theme.dart';
import 'package:smart_attendance/core/utils/camera_helper.dart';
import 'package:smart_attendance/core/widgets/oval_guide_painter.dart';

class FaceVerificationScreen extends ConsumerStatefulWidget {
  const FaceVerificationScreen({super.key});

  @override
  ConsumerState<FaceVerificationScreen> createState() => _FaceVerificationScreenState();
}

class _FaceVerificationScreenState extends ConsumerState<FaceVerificationScreen> {
  CameraController? _cameraController;
  FaceDetector? _faceDetector;
  bool _isCameraInitialized = false;
  bool _isCameraError = false;
  bool _isProcessingFrame = false;
  bool _simulatorMode = false;
  bool _showResult = false;
  bool _isVerified = false;

  String _instructionMessage = 'Align your face inside the oval';
  Color _ovalColor = Colors.white;

  static const String _mockJpegBase64 = 
      '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCABkAGQBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=';

  @override
  void initState() {
    super.initState();
    if (!kIsWeb) {
      _initDetector();
    }
    _initCamera();
  }

  void _initDetector() {
    _faceDetector = FaceDetector(
      options: FaceDetectorOptions(
        enableClassification: true,
        enableTracking: true,
        performanceMode: FaceDetectorMode.accurate,
      ),
    );
  }

  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        throw Exception('No cameras');
      }

      final frontCam = cameras.firstWhere(
        (cam) => cam.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );

      _cameraController = CameraController(
        frontCam,
        ResolutionPreset.medium,
        enableAudio: false,
      );

      await _cameraController!.initialize();
      if (!mounted) return;

      setState(() {
        _isCameraInitialized = true;
        _isCameraError = false;
      });

      if (!kIsWeb) {
        _startDetectionStream();
      }
    } catch (e) {
      debugPrint('Verification camera error: $e');
      setState(() {
        _isCameraError = true;
        _simulatorMode = true;
      });
    }
  }

  void _startDetectionStream() {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;

    _cameraController!.startImageStream((CameraImage image) async {
      if (_isProcessingFrame || _simulatorMode || _showResult) return;
      _isProcessingFrame = true;

      try {
        final inputImage = _convertCameraImage(image);
        if (inputImage == null) {
          _isProcessingFrame = false;
          return;
        }

        final faces = await _faceDetector!.processImage(inputImage);
        if (!mounted) return;

        _validateFace(faces);
      } catch (e) {
        debugPrint('Verification stream error: $e');
      } finally {
        _isProcessingFrame = false;
      }
    });
  }

  InputImage? _convertCameraImage(CameraImage image) {
    try {
      final WriteBuffer allBytes = WriteBuffer();
      for (final Plane plane in image.planes) {
        allBytes.putUint8List(plane.bytes);
      }
      final bytes = allBytes.done().buffer.asUint8List();

      final Size imageSize = Size(image.width.toDouble(), image.height.toDouble());
      final camera = _cameraController!.description;
      final imageRotation = InputImageRotationValue.fromRawValue(camera.sensorOrientation) ?? InputImageRotation.rotation0deg;
      final inputImageFormat = InputImageFormatValue.fromRawValue(image.format.raw) ?? InputImageFormat.nv21;

      final inputImageMetadata = InputImageMetadata(
        size: imageSize,
        rotation: imageRotation,
        format: inputImageFormat,
        bytesPerRow: image.planes[0].bytesPerRow,
      );

      return InputImage.fromBytes(bytes: bytes, metadata: inputImageMetadata);
    } catch (_) {
      return null;
    }
  }

  void _validateFace(List<Face> faces) {
    if (faces.isEmpty) {
      setState(() {
        _instructionMessage = 'Place your face in the oval guide';
        _ovalColor = Colors.red;
      });
      return;
    }

    if (faces.length > 1) {
      setState(() {
        _instructionMessage = 'Multiple faces. Ensure single face in frame.';
        _ovalColor = Colors.red;
      });
      return;
    }

    final face = faces.first;
    
    final leftEyeOpen = face.leftEyeOpenProbability ?? 1.0;
    final rightEyeOpen = face.rightEyeOpenProbability ?? 1.0;
    
    if (leftEyeOpen < 0.75 || rightEyeOpen < 0.75) {
      setState(() {
        _instructionMessage = 'Keep your eyes open';
        _ovalColor = Colors.yellow;
      });
      return;
    }

    final double yaw = face.headEulerAngleY ?? 0.0;
    final double pitch = face.headEulerAngleX ?? 0.0;

    final isFrontal = yaw.abs() < 8.0 && pitch.abs() < 8.0;

    if (isFrontal) {
      setState(() {
        _ovalColor = Colors.green;
        _instructionMessage = 'Hold still, verifying...';
      });
      _captureAndVerify();
    } else {
      setState(() {
        _ovalColor = Colors.white;
        _instructionMessage = 'Look straight at the camera';
      });
    }
  }

  Future<void> _captureAndVerify() async {
    if (_cameraController == null) return;
    
    try {
      if (!kIsWeb) {
        await _cameraController!.stopImageStream();
      }
      
      final image = await _cameraController!.takePicture();
      final bytes = await image.readAsBytes();
      
      await _safeExit();
      
      _submitVerifyBytes(bytes);
    } catch (e) {
      debugPrint('Shutter error: $e');
      if (!kIsWeb) {
        _startDetectionStream();
      }
    }
  }

  void _simulateVerify() async {
    final validBytes = base64Decode(_mockJpegBase64);
    await _safeExit();
    _submitVerifyBytes(validBytes);
  }

  void _submitVerifyBytes(List<int> bytes) async {
    final kioskState = ref.read(studentProvider);
    final student = kioskState.selectedStudent;
    final clazz = kioskState.selectedClass;

    if (student == null || clazz == null) {
      setState(() {
        _showResult = true;
        _isVerified = false;
      });
      return;
    }

    final deviceInfo = kIsWeb ? 'Web Browser' : (Platform.isAndroid ? 'Android Device' : 'iOS Device');
    
    final success = await ref.read(faceProvider.notifier).verifyFace(
      bytes: bytes,
      studentId: student.studentId,
      classId: clazz.classId,
      deviceInfo: deviceInfo,
    );

    setState(() {
      _showResult = true;
      _isVerified = success;
    });
  }

  void _resetVerification() {
    setState(() {
      _showResult = false;
      _instructionMessage = 'Align your face inside the oval';
      _ovalColor = Colors.white;
    });
    ref.read(faceProvider.notifier).resetProcess();
    if (!_simulatorMode) {
      _initCamera();
    }
  }

  Future<void> _safeExit() async {
    if (_cameraController != null) {
      try {
        await _cameraController!.dispose();
      } catch (e) {
        debugPrint('Controller dispose error: $e');
      }
      _cameraController = null;
    }
    _faceDetector?.close();
    if (kIsWeb) {
      forceStopWebcamStreams();
    }
    
    if (mounted) {
      setState(() {
        _isCameraInitialized = false;
      });
    }
  }

  @override
  void dispose() {
    _safeExit();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final faceState = ref.watch(faceProvider);
    final kioskState = ref.watch(studentProvider);
    final student = kioskState.selectedStudent;

    if (student == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Face Verification')),
        body: const Center(child: Text('No student selected. Please select a student first.')),
      );
    }

    return PopScope(
      canPop: true,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) {
          await _safeExit();
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text('Verifying ${student.name}'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () async {
              await _safeExit();
              if (context.mounted) {
                context.pop();
              }
            },
          ),
          actions: [
            Switch(
              value: _simulatorMode,
              onChanged: (val) async {
                if (val) {
                  await _safeExit();
                }
                setState(() {
                  _simulatorMode = val;
                  if (!_simulatorMode) {
                    _initCamera();
                  }
                });
              },
            ),
            const Padding(
              padding: EdgeInsets.only(right: 8.0),
              child: Center(child: Text('Sim', style: TextStyle(fontSize: 12))),
            )
          ],
        ),
        body: faceState.isLoading
            ? const Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 16),
                    Text('Analyzing face biometrics...'),
                  ],
                ),
              )
            : _showResult
                ? _buildResultView(faceState, student.name)
                : Stack(
                    children: [
                      if (_isCameraInitialized && !_simulatorMode)
                        Positioned.fill(
                          child: AspectRatio(
                            aspectRatio: _cameraController!.value.aspectRatio,
                            child: CameraPreview(_cameraController!),
                          ),
                        )
                      else
                        Positioned.fill(
                          child: Container(
                            color: Colors.black87,
                            child: const Center(
                              child: Icon(Icons.videocam_off_rounded, size: 70, color: Colors.white30),
                            ),
                          ),
                        ),

                      Positioned.fill(
                        child: CustomPaint(
                          painter: OvalGuidePainter(
                            borderColor: _ovalColor,
                            isFaceDetected: _ovalColor == Colors.green || _ovalColor == Colors.yellow,
                          ),
                        ),
                      ),

                      Positioned(
                        top: 20,
                        left: 20,
                        right: 20,
                        child: Card(
                          color: Colors.black.withOpacity(0.7),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
                            child: Text(
                              !_simulatorMode
                                  ? 'Align your face and tap the button below'
                                  : _instructionMessage,
                              textAlign: TextAlign.center,
                              style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ),
                      ),

                      if (_simulatorMode)
                        Positioned(
                          bottom: 50,
                          left: 40,
                          right: 40,
                          child: ElevatedButton.icon(
                            onPressed: _simulateVerify,
                            icon: const Icon(Icons.flash_on_rounded),
                            label: const Text('Simulate Verification Capture'),
                          ),
                        )
                      else if (_isCameraInitialized)
                        Positioned(
                          bottom: 50,
                          left: 40,
                          right: 40,
                          child: ElevatedButton.icon(
                            onPressed: _captureAndVerify,
                            icon: const Icon(Icons.camera_alt_rounded),
                            label: const Text('Capture & Verify Real Face'),
                          ),
                        ),
                    ],
                  ),
      ),
    );
  }

  Widget _buildResultView(FaceProcessState faceState, String studentName) {
    final title = _isVerified ? 'VERIFICATION SUCCESS' : 'VERIFICATION FAILED';
    final color = _isVerified ? Colors.green : AppTheme.errorColor;
    final message = _isVerified
        ? 'Identity confirmed for $studentName. Similarity threshold matched.'
        : (faceState.error ?? 'Face profile did not match registered records.');

    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Icon(
            _isVerified ? Icons.check_circle_outline_rounded : Icons.cancel_outlined,
            size: 100,
            color: color,
          ),
          const SizedBox(height: 24),
          Text(
            title,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: color),
          ),
          const SizedBox(height: 8),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 15, color: Colors.grey),
          ),
          const SizedBox(height: 40),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                children: [
                  const Text('MATCH SCORES', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.grey)),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildScoreCircle('Similarity', faceState.similarityScore),
                      _buildScoreCircle('Confidence', faceState.confidenceScore),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 48),
          ElevatedButton(
            onPressed: _resetVerification,
            child: const Text('Try Again'),
          ),
          const SizedBox(height: 12),
          OutlinedButton(
            onPressed: () async {
              await _safeExit();
              ref.read(studentProvider.notifier).reset();
              if (mounted) {
                context.go('/select-class');
              }
            },
            child: const Text('Back to Home'),
          ),
        ],
      ),
    );
  }

  Widget _buildScoreCircle(String label, double score) {
    final percent = (score * 100).toStringAsFixed(0);
    return Column(
      children: [
        Stack(
          alignment: Alignment.center,
          children: [
            SizedBox(
              height: 70,
              width: 70,
              child: CircularProgressIndicator(
                value: score.clamp(0.0, 1.0),
                strokeWidth: 6,
                backgroundColor: Colors.grey.withOpacity(0.2),
                color: _isVerified ? Colors.green : AppTheme.errorColor,
              ),
            ),
            Text(
              '$percent%',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Text(label, style: const TextStyle(fontSize: 13)),
      ],
    );
  }
}
