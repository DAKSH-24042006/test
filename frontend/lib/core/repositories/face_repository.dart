import 'package:dio/dio';
import 'package:smart_attendance/core/services/dio_client.dart';

class FaceRepository {
  final DioClient _client = DioClient();

  Future<Map<String, dynamic>> verifyFace({
    required List<int> imageBytes,
    required String studentId,
    required String classId,
    required String deviceInfo,
  }) async {
    try {
      final formData = FormData.fromMap({
        'student_id': studentId,
        'class_id': classId,
        'image': MultipartFile.fromBytes(
          imageBytes,
          filename: 'verify.jpg',
          contentType: DioMediaType('image', 'jpeg'),
        ),
        'device_info': deviceInfo,
      });

      final response = await _client.dio.post(
        '/verify',
        data: formData,
        options: Options(contentType: 'multipart/form-data'),
      );

      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Exception _handleDioError(DioException e) {
    if (e.response != null && e.response?.data != null) {
      final detail = e.response?.data['detail'];
      if (detail != null) {
        return Exception(detail.toString());
      }
    }
    return Exception('Biometric matching service error. Please try again.');
  }
}
