import 'package:dio/dio.dart';
import 'package:smart_attendance/core/models/class_model.dart';
import 'package:smart_attendance/core/models/student_model.dart';
import 'package:smart_attendance/core/services/dio_client.dart';

class StudentRepository {
  final DioClient _client = DioClient();

  Future<List<ClassModel>> getClasses() async {
    try {
      final response = await _client.dio.get('/classes');
      return (response.data as List).map((c) => ClassModel.fromJson(c)).toList();
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Future<List<StudentModel>> getStudentsInClass(String classId) async {
    try {
      final response = await _client.dio.get('/students', queryParameters: {'class': classId});
      return (response.data as List).map((s) => StudentModel.fromJson(s)).toList();
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
    return Exception('Connection error. Please try again.');
  }
}
