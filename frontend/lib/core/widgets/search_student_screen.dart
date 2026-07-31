import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:smart_attendance/core/providers/student_provider.dart';

class SearchStudentScreen extends ConsumerStatefulWidget {
  const SearchStudentScreen({super.key});

  @override
  ConsumerState<SearchStudentScreen> createState() => _SearchStudentScreenState();
}

class _SearchStudentScreenState extends ConsumerState<SearchStudentScreen> {
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final kioskState = ref.watch(studentProvider);
    final selectedClass = kioskState.selectedClass;

    if (selectedClass == null) {
      return const Scaffold(
        body: Center(child: Text('No class selected. Please go back.')),
      );
    }

    // Filter students locally based on search query
    final filteredStudents = kioskState.students.where((student) {
      final nameMatches = student.name.toLowerCase().contains(_searchQuery.toLowerCase());
      final regMatches = student.regNo.toLowerCase().contains(_searchQuery.toLowerCase());
      return nameMatches || regMatches;
    }).toList();

    return Scaffold(
      appBar: AppBar(
        title: Text(selectedClass.className),
        centerTitle: true,
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Theme.of(context).colorScheme.surface,
              Theme.of(context).colorScheme.surfaceContainerHighest.withOpacity(0.4),
            ],
          ),
        ),
        child: Column(
          children: [
            // Search Input Header
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: SearchBar(
                controller: _searchController,
                onChanged: (val) {
                  setState(() {
                    _searchQuery = val;
                  });
                },
                hintText: 'Search student name or Reg. No...',
                leading: const Icon(Icons.search_rounded),
                trailing: [
                  if (_searchQuery.isNotEmpty)
                    IconButton(
                      icon: const Icon(Icons.clear_rounded),
                      onPressed: () {
                        _searchController.clear();
                        setState(() {
                          _searchQuery = '';
                        });
                      },
                    ),
                ],
              ),
            ),
            
            // Student List
            Expanded(
              child: kioskState.isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : filteredStudents.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.person_search_rounded, size: 64, color: Colors.grey),
                              const SizedBox(height: 16),
                              Text(
                                _searchQuery.isEmpty ? 'No students registered' : 'No matching students found',
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.grey),
                              ),
                            ],
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.symmetric(horizontal: 16.0),
                          itemCount: filteredStudents.length,
                          itemBuilder: (context, index) {
                            final student = filteredStudents[index];
                            return Card(
                              margin: const EdgeInsets.only(bottom: 12),
                              elevation: 1,
                              child: ListTile(
                                leading: CircleAvatar(
                                  backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                                  child: Text(
                                    student.name.isNotEmpty ? student.name[0].toUpperCase() : 'S',
                                    style: TextStyle(
                                      color: Theme.of(context).colorScheme.onPrimaryContainer,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                                title: Text(
                                  student.name,
                                  style: const TextStyle(fontWeight: FontWeight.bold),
                                ),
                                subtitle: Text(student.regNo),
                                trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 16),
                                onTap: () {
                                  ref.read(studentProvider.notifier).selectStudent(student);
                                  context.push('/face-verification');
                                },
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
