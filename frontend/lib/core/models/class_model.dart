class ClassModel {
  final String classId;
  final String className;
  final String department;
  final int semester;
  final String section;

  ClassModel({
    required this.classId,
    required this.className,
    required this.department,
    required this.semester,
    required this.section,
  });

  factory ClassModel.fromJson(Map<String, dynamic> json) {
    return ClassModel(
      classId: json['class_id'] ?? json['_id'] ?? '',
      className: json['class_name'] ?? json['classCode'] ?? '',
      department: json['department'] ?? '',
      semester: json['semester'] ?? 1,
      section: json['section'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'class_id': classId,
      'class_name': className,
      'department': department,
      'semester': semester,
      'section': section,
    };
  }

  String get displayName => '$className - Sem $semester ($section)';
}
