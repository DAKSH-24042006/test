import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:smart_attendance/core/repositories/face_repository.dart';

class FaceProcessState {
  final bool isLoading;
  final bool? verificationSuccess;
  final double similarityScore;
  final double confidenceScore;
  final String? error;

  FaceProcessState({
    required this.isLoading,
    this.verificationSuccess,
    this.similarityScore = 0.0,
    this.confidenceScore = 0.0,
    this.error,
  });

  factory FaceProcessState.initial() => FaceProcessState(isLoading: false);

  FaceProcessState copyWith({
    bool? isLoading,
    bool? verificationSuccess,
    double? similarityScore,
    double? confidenceScore,
    String? error,
  }) {
    return FaceProcessState(
      isLoading: isLoading ?? this.isLoading,
      verificationSuccess: verificationSuccess ?? this.verificationSuccess,
      similarityScore: similarityScore ?? this.similarityScore,
      confidenceScore: confidenceScore ?? this.confidenceScore,
      error: error,
    );
  }
}

class FaceNotifier extends StateNotifier<FaceProcessState> {
  final FaceRepository _faceRepo = FaceRepository();

  FaceNotifier() : super(FaceProcessState.initial());

  void resetProcess() {
    state = FaceProcessState.initial();
  }

  Future<bool> verifyFace({
    required List<int> bytes,
    required String studentId,
    required String classId,
    required String deviceInfo,
  }) async {
    state = state.copyWith(isLoading: true, error: null, verificationSuccess: null);
    try {
      final res = await _faceRepo.verifyFace(
        imageBytes: bytes,
        studentId: studentId,
        classId: classId,
        deviceInfo: deviceInfo,
      );
      state = state.copyWith(
        isLoading: false,
        verificationSuccess: res['verified'] ?? false,
        similarityScore: (res['similarityScore'] as num?)?.toDouble() ?? 0.0,
        confidenceScore: (res['confidence'] as num?)?.toDouble() ?? 0.0,
      );
      return res['verified'] ?? false;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
      );
      return false;
    }
  }
}

final faceProvider = StateNotifierProvider<FaceNotifier, FaceProcessState>((ref) {
  return FaceNotifier();
});
