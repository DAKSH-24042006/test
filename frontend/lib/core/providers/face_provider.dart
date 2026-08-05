import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:smart_attendance/core/repositories/face_repository.dart';

class FaceProcessState {
  final bool isLoading;
  final bool? verificationSuccess;
  final bool? livenessPassed;
  final bool? antiSpoofPassed;
  final double similarityScore;
  final double confidenceScore;
  final String? error;

  // Liveness session data
  final String? sessionId;
  final String? nonce;
  final List<String> challenges;
  final List<String> challengeDescriptions;

  FaceProcessState({
    required this.isLoading,
    this.verificationSuccess,
    this.livenessPassed,
    this.antiSpoofPassed,
    this.similarityScore = 0.0,
    this.confidenceScore = 0.0,
    this.error,
    this.sessionId,
    this.nonce,
    this.challenges = const [],
    this.challengeDescriptions = const [],
  });

  factory FaceProcessState.initial() => FaceProcessState(isLoading: false);

  FaceProcessState copyWith({
    bool? isLoading,
    bool? verificationSuccess,
    bool? livenessPassed,
    bool? antiSpoofPassed,
    double? similarityScore,
    double? confidenceScore,
    String? error,
    String? sessionId,
    String? nonce,
    List<String>? challenges,
    List<String>? challengeDescriptions,
  }) {
    return FaceProcessState(
      isLoading: isLoading ?? this.isLoading,
      verificationSuccess: verificationSuccess ?? this.verificationSuccess,
      livenessPassed: livenessPassed ?? this.livenessPassed,
      antiSpoofPassed: antiSpoofPassed ?? this.antiSpoofPassed,
      similarityScore: similarityScore ?? this.similarityScore,
      confidenceScore: confidenceScore ?? this.confidenceScore,
      error: error,
      sessionId: sessionId ?? this.sessionId,
      nonce: nonce ?? this.nonce,
      challenges: challenges ?? this.challenges,
      challengeDescriptions: challengeDescriptions ?? this.challengeDescriptions,
    );
  }
}

class FaceNotifier extends StateNotifier<FaceProcessState> {
  final FaceRepository _faceRepo = FaceRepository();

  FaceNotifier() : super(FaceProcessState.initial());

  void resetProcess() {
    state = FaceProcessState.initial();
  }

  Future<Map<String, dynamic>?> startLivenessSession(String studentId) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final res = await _faceRepo.startLivenessSession(studentId);
      final sessionId = res['session_id'] as String?;
      final nonce = res['nonce'] as String?;
      final challenges = (res['challenges'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];
      final descriptions = (res['challenge_descriptions'] as List<dynamic>?)?.map((e) => e.toString()).toList() ?? [];

      state = state.copyWith(
        isLoading: false,
        sessionId: sessionId,
        nonce: nonce,
        challenges: challenges,
        challengeDescriptions: descriptions,
      );
      return res;
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
      );
      return null;
    }
  }

  Future<bool> verifyWithLiveness({
    required String studentId,
    required String classId,
    required String sessionId,
    required String nonce,
    required List<List<int>> framesBytes,
    required String deviceInfo,
  }) async {
    state = state.copyWith(isLoading: true, error: null, verificationSuccess: null);
    try {
      final res = await _faceRepo.verifyWithLiveness(
        studentId: studentId,
        classId: classId,
        sessionId: sessionId,
        nonce: nonce,
        framesBytes: framesBytes,
        deviceInfo: deviceInfo,
      );

      final verified = res['verified'] ?? false;
      state = state.copyWith(
        isLoading: false,
        verificationSuccess: verified,
        livenessPassed: res['livenessPassed'] ?? false,
        antiSpoofPassed: res['antiSpoofPassed'] ?? false,
        similarityScore: (res['similarityScore'] as num?)?.toDouble() ?? 0.0,
        confidenceScore: (res['confidence'] as num?)?.toDouble() ?? 0.0,
        error: verified ? null : (res['message'] ?? 'Verification failed'),
      );
      return verified;
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
