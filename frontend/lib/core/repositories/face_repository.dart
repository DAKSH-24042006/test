import 'package:dio/dio.dart';
import 'package:smart_attendance/core/services/dio_client.dart';

class FaceRepository {
  final DioClient _client = DioClient();

  Future<Map<String, dynamic>> startLivenessSession(String studentId) async {
    try {
      final response = await _client.dio.post(
        '/start-liveness-session',
        data: {'student_id': studentId},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw handleDioError(e);
    }
  }

  Future<Map<String, dynamic>> verifyWithLiveness({
    required String studentId,
    required String classId,
    required String sessionId,
    required String nonce,
    required List<List<int>> framesBytes,
    required String deviceInfo,
  }) async {
    try {
      final List<MultipartFile> imageFiles = [];
      for (int i = 0; i < framesBytes.length; i++) {
        imageFiles.add(MultipartFile.fromBytes(
          framesBytes[i],
          filename: 'scan_frame_$i.jpg',
          contentType: DioMediaType('image', 'jpeg'),
        ));
      }

      final formData = FormData.fromMap({
        'student_id': studentId,
        'class_id': classId,
        'session_id': sessionId,
        'nonce': nonce,
        'images': imageFiles,
        'device_info': deviceInfo,
      });

      final response = await _client.dio.post(
        '/verify-with-liveness',
        data: formData,
        options: Options(contentType: 'multipart/form-data'),
      );

      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw handleDioError(e);
    }
  }

  Exception handleDioError(DioException e) {
    if (e.response != null && e.response?.data != null) {
      final detail = e.response?.data['detail'];
      if (detail != null) {
        return Exception(detail.toString());
      }
    }
    return Exception('Biometric matching service error. Please try again.');
  }
}
