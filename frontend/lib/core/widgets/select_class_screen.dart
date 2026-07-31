import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:smart_attendance/core/providers/student_provider.dart';
import 'package:smart_attendance/core/theme/app_theme.dart';

class SelectClassScreen extends ConsumerStatefulWidget {
  const SelectClassScreen({super.key});

  @override
  ConsumerState<SelectClassScreen> createState() => _SelectClassScreenState();
}

class _SelectClassScreenState extends ConsumerState<SelectClassScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(studentProvider.notifier).fetchClasses();
    });
  }

  @override
  Widget build(BuildContext context) {
    final kioskState = ref.watch(studentProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Select Class Kiosk'),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => context.push('/settings'),
          ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => ref.read(studentProvider.notifier).fetchClasses(),
          ),
        ],
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
        child: kioskState.isLoading
            ? const Center(child: CircularProgressIndicator())
            : kioskState.error != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.cloud_off_rounded, size: 64, color: Theme.of(context).colorScheme.error),
                          const SizedBox(height: 16),
                          Text(
                            'Connection Error',
                            style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            kioskState.error!,
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey),
                          ),
                          const SizedBox(height: 24),
                          ElevatedButton.icon(
                            onPressed: () => ref.read(studentProvider.notifier).fetchClasses(),
                            icon: const Icon(Icons.refresh),
                            label: const Text('Try Again'),
                          ),
                        ],
                      ),
                    ),
                  )
                : kioskState.classes.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.school_outlined, size: 64, color: Colors.grey),
                            const SizedBox(height: 16),
                            Text(
                              'No Classes Programmed',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(color: Colors.grey),
                            ),
                          ],
                        ),
                      )
                    : RefreshIndicator(
                        onRefresh: () => ref.read(studentProvider.notifier).fetchClasses(),
                        child: ListView.builder(
                          padding: const EdgeInsets.all(20.0),
                          itemCount: kioskState.classes.length,
                          itemBuilder: (context, index) {
                            final clazz = kioskState.classes[index];
                            return Card(
                              margin: const EdgeInsets.only(bottom: 16),
                              elevation: 2,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(16),
                                side: BorderSide(
                                  color: Theme.of(context).colorScheme.outline.withOpacity(0.1),
                                ),
                              ),
                              child: InkWell(
                                borderRadius: BorderRadius.circular(16),
                                onTap: () async {
                                  await ref.read(studentProvider.notifier).selectClass(clazz);
                                  if (mounted) {
                                    context.push('/search-student');
                                  }
                                },
                                child: Padding(
                                  padding: const EdgeInsets.all(20.0),
                                  child: Row(
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.all(12),
                                        decoration: BoxDecoration(
                                          color: Theme.of(context).colorScheme.primaryContainer,
                                          borderRadius: BorderRadius.circular(12),
                                        ),
                                        child: Icon(
                                          Icons.class_rounded,
                                          color: Theme.of(context).colorScheme.onPrimaryContainer,
                                        ),
                                      ),
                                      const SizedBox(width: 16),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              clazz.className,
                                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                                    fontWeight: FontWeight.bold,
                                                  ),
                                            ),
                                            const SizedBox(height: 4),
                                            Text(
                                              '${clazz.department} • Semester ${clazz.semester} • Section ${clazz.section}',
                                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                                    color: Colors.grey[600],
                                                  ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      Icon(
                                        Icons.chevron_right_rounded,
                                        color: Theme.of(context).colorScheme.primary,
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
                      ),
      ),
    );
  }
}
