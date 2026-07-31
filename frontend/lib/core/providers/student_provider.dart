import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:smart_attendance/core/models/class_model.dart';
import 'package:smart_attendance/core/models/student_model.dart';
import 'package:smart_attendance/core/repositories/student_repository.dart';

class KioskState {
  final bool isLoading;
  final List<ClassModel> classes;
  final ClassModel? selectedClass;
  final List<StudentModel> students;
  final StudentModel? selectedStudent;
  final String? error;

  KioskState({
    required this.isLoading,
    this.classes = const [],
    this.selectedClass,
    this.students = const [],
    this.selectedStudent,
    this.error,
  });

  factory KioskState.initial() => KioskState(isLoading: false);

  KioskState copyWith({
    bool? isLoading,
    List<ClassModel>? classes,
    ClassModel? selectedClass,
    List<StudentModel>? students,
    StudentModel? selectedStudent,
    String? error,
  }) {
    return KioskState(
      isLoading: isLoading ?? this.isLoading,
      classes: classes ?? this.classes,
      selectedClass: selectedClass ?? this.selectedClass,
      students: students ?? this.students,
      selectedStudent: selectedStudent ?? this.selectedStudent,
      error: error,
    );
  }
}

class KioskNotifier extends StateNotifier<KioskState> {
  final StudentRepository _studentRepo = StudentRepository();

  KioskNotifier() : super(KioskState.initial());

  Future<void> fetchClasses() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final list = await _studentRepo.getClasses();
      state = state.copyWith(
        isLoading: false,
        classes: list,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
      );
    }
  }

  Future<void> selectClass(ClassModel clazz) async {
    state = state.copyWith(
      selectedClass: clazz,
      selectedStudent: null,
      students: [],
    );
    await fetchStudents(clazz.classId);
  }

  Future<void> fetchStudents(String classId) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final list = await _studentRepo.getStudentsInClass(classId);
      state = state.copyWith(
        isLoading: false,
        students: list,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceAll('Exception: ', ''),
      );
    }
  }

  void selectStudent(StudentModel student) {
    state = state.copyWith(selectedStudent: student);
  }

  void reset() {
    state = KioskState.initial();
  }
}

final studentProvider = StateNotifierProvider<KioskNotifier, KioskState>((ref) {
  return KioskNotifier();
});
