import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:smart_attendance/core/theme/app_theme.dart';
import 'package:smart_attendance/core/services/dio_client.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  late final TextEditingController _urlController;

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(text: DioClient.baseUrl);
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  void _saveUrl() {
    final url = _urlController.text.trim();
    if (url.isNotEmpty) {
      DioClient.setBaseUrl(url);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Server endpoint updated to: $url'),
          backgroundColor: Colors.green,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final themeMode = ref.watch(themeProvider);
    final isDark = themeMode == ThemeMode.dark ||
        (themeMode == ThemeMode.system && MediaQuery.of(context).platformBrightness == Brightness.dark);

    return Scaffold(
      appBar: AppBar(
        title: const Text('System Settings'),
      ),
      body: ListView(
        children: [
          const SizedBox(height: 16),
          // Theme Section
          _buildSectionHeader('Appearance'),
          SwitchListTile(
            title: const Text('Dark Mode Theme'),
            subtitle: const Text('Switch between dark and light themes'),
            secondary: Icon(isDark ? Icons.dark_mode_rounded : Icons.light_mode_rounded),
            value: isDark,
            onChanged: (val) {
              ref.read(themeProvider.notifier).toggleTheme(val);
            },
          ),
          const Divider(),
          // Server endpoint section
          _buildSectionHeader('Developer Network Configurations'),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'FastAPI Base Server Endpoint URL',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.grey),
                ),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _urlController,
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.dns_outlined),
                    hintText: 'http://localhost:8000/api/v1',
                  ),
                ),
                const SizedBox(height: 12),
                ElevatedButton.icon(
                  onPressed: _saveUrl,
                  icon: const Icon(Icons.save_rounded),
                  label: const Text('Save Server URL'),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Default Emulator loops: Android utilizes http://10.0.2.2:8000, while iOS/Web utilizes http://localhost:8000.',
                  style: TextStyle(fontSize: 12, color: Colors.grey, fontStyle: FontStyle.italic),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
          const Divider(),
          // System details
          _buildSectionHeader('Version Information'),
          const ListTile(
            leading: Icon(Icons.info_outline_rounded),
            title: Text('Shield Core V1.0'),
            subtitle: Text('Enterprise Smart Attendance Biometric Suite'),
            trailing: Text('v1.0.0'),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
      child: Text(
        title.toUpperCase(),
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: Theme.of(context).colorScheme.secondary,
          letterSpacing: 1.2,
        ),
      ),
    );
  }
}
