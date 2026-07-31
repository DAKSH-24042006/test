import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:smart_attendance/core/services/secure_storage_service.dart';

class DioClient {
  late final Dio dio;
  final SecureStorageService _storage = SecureStorageService();
  
  // Set the server endpoint. Custom servers can be configured in settings.
  static String baseUrl = kIsWeb
      ? 'http://localhost:8000/api/v1'
      : (Platform.isAndroid ? 'http://10.0.2.2:8000/api/v1' : 'http://localhost:8000/api/v1');

  DioClient() {
    dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 15),
      contentType: 'application/json',
    ));

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          // Retrieve and attach access token
          final token = await _storage.getAccessToken();
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (DioException error, handler) async {
          // If token expired (401 Unauthorized), attempt refresh
          if (error.response?.statusCode == 401 && 
              !error.requestOptions.path.contains('/auth/login') &&
              !error.requestOptions.path.contains('/auth/refresh')) {
            
            final success = await _attemptTokenRefresh();
            if (success) {
              // Retry the original request with new access token
              final token = await _storage.getAccessToken();
              final opts = Options(
                method: error.requestOptions.method,
                headers: error.requestOptions.headers..['Authorization'] = 'Bearer $token',
              );
              
              try {
                final response = await dio.request(
                  error.requestOptions.path,
                  data: error.requestOptions.data,
                  queryParameters: error.requestOptions.queryParameters,
                  options: opts,
                );
                return handler.resolve(response);
              } on DioException catch (retryError) {
                return handler.next(retryError);
              }
            }
          }
          return handler.next(error);
        },
      ),
    );
  }

  Future<bool> _attemptTokenRefresh() async {
    final refreshToken = await _storage.getRefreshToken();
    if (refreshToken == null) return false;

    try {
      // Create separate Dio instance to avoid interceptor loop
      final refreshDio = Dio(BaseOptions(baseUrl: baseUrl));
      final response = await refreshDio.post('/auth/refresh', data: {
        'refreshToken': refreshToken,
      });

      if (response.statusCode == 200) {
        final data = response.data;
        final newAccess = data['accessToken'] as String;
        final newRefresh = data['refreshToken'] as String;
        await _storage.saveTokens(accessToken: newAccess, refreshToken: newRefresh);
        return true;
      }
    } catch (e) {
      debugPrint('Failed to refresh authentication token: $e');
    }

    // Refresh failed or revoked - clear session
    await _storage.clearSession();
    return false;
  }

  // Helper to dynamically update the server address
  static void setBaseUrl(String newUrl) {
    baseUrl = newUrl;
  }
}
