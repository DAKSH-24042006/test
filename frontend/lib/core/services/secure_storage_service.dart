import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:smart_attendance/core/models/user_model.dart';

class SecureStorageService {
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  static const String _keyAccessToken = 'access_token';
  static const String _keyRefreshToken = 'refresh_token';
  static const String _keyUser = 'cached_user';
  static const String _keyThemeMode = 'theme_mode';

  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {
    await _storage.write(key: _keyAccessToken, value: accessToken);
    await _storage.write(key: _keyRefreshToken, value: refreshToken);
  }

  Future<String?> getAccessToken() async {
    return await _storage.read(key: _keyAccessToken);
  }

  Future<String?> getRefreshToken() async {
    return await _storage.read(key: _keyRefreshToken);
  }

  Future<void> cacheUser(UserModel user) async {
    final userJson = jsonEncode(user.toJson());
    await _storage.write(key: _keyUser, value: userJson);
  }

  Future<UserModel?> getCachedUser() async {
    final userJson = await _storage.read(key: _keyUser);
    if (userJson == null) return null;
    try {
      final userMap = jsonDecode(userJson) as Map<String, dynamic>;
      return UserModel.fromJson(userMap);
    } catch (_) {
      return null;
    }
  }

  Future<void> clearSession() async {
    await _storage.delete(key: _keyAccessToken);
    await _storage.delete(key: _keyRefreshToken);
    await _storage.delete(key: _keyUser);
  }

  Future<void> saveThemeMode(String mode) async {
    await _storage.write(key: _keyThemeMode, value: mode);
  }

  Future<String?> getThemeMode() async {
    return await _storage.read(key: _keyThemeMode);
  }
}
