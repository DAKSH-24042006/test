import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:smart_attendance/core/widgets/splash_screen.dart';
import 'package:smart_attendance/core/widgets/settings_screen.dart';
import 'package:smart_attendance/core/widgets/select_class_screen.dart';
import 'package:smart_attendance/core/widgets/search_student_screen.dart';
import 'package:smart_attendance/face/face_verification_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/select-class',
        builder: (context, state) => const SelectClassScreen(),
      ),
      GoRoute(
        path: '/search-student',
        builder: (context, state) => const SearchStudentScreen(),
      ),
      GoRoute(
        path: '/face-verification',
        builder: (context, state) => const FaceVerificationScreen(),
      ),
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SettingsScreen(),
      ),
    ],
  );
});
