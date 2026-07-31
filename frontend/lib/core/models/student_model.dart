class StudentModel {
  final String studentId;
  final String classId;
  final String regNo;
  final String name;

  StudentModel({
    required this.studentId,
    required this.classId,
    required this.regNo,
    required this.name,
  });

  factory StudentModel.fromJson(Map<String, dynamic> json) {
    return StudentModel(
      studentId: json['student_id'] ?? json['_id'] ?? '',
      classId: json['class_id'] ?? '',
      regNo: json['reg_no'] ?? json['registrationNumber'] ?? '',
      name: json['name'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'student_id': studentId,
      'class_id': classId,
      'reg_no': regNo,
      'name': name,
    };
  }
}
