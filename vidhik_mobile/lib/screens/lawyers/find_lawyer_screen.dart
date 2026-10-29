import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class LawyerDirectoryScreen extends StatefulWidget {
  const LawyerDirectoryScreen({super.key});

  @override
  State<LawyerDirectoryScreen> createState() => _LawyerDirectoryScreenState();
}

class _LawyerDirectoryScreenState extends State<LawyerDirectoryScreen> {
  final _search = TextEditingController();
  late Future<List<Map<String, dynamic>>> _future;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().lawyerDirectory();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  void _reload() {
    setState(() {
      _future = context.read<ApiService>().lawyerDirectory(
        search: _query.isEmpty ? null : _query,
      );
    });
  }

  Future<void> _launch(String scheme, String value) async {
    if (value.trim().isEmpty) return;
    final uri = Uri.parse('$scheme:${value.replaceAll(' ', '')}');
    final ok = await launchUrl(uri);
    if (!ok && mounted) showInfoSnack(context, value);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Find a lawyer'),
        actions: [
          IconButton(onPressed: _reload, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
            child: TextField(
              controller: _search,
              textInputAction: TextInputAction.search,
              onSubmitted: (value) {
                _query = value.trim();
                _reload();
              },
              decoration: InputDecoration(
                hintText: 'Search by name, city or specialization',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  onPressed: _reload,
                  icon: const Icon(Icons.arrow_forward),
                ),
              ),
            ),
          ),
          Expanded(
            child: FutureBuilder<List<Map<String, dynamic>>>(
              future: _future,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(
                    child: CircularProgressIndicator(strokeWidth: 2.4),
                  );
                }
                if (snapshot.hasError) {
                  return ErrorState(
                    message: '${snapshot.error}'.replaceFirst(
                      'ApiException: ',
                      '',
                    ),
                    onRetry: _reload,
                  );
                }
                final lawyers = snapshot.data ?? const [];
                if (lawyers.isEmpty) {
                  return const EmptyState(
                    title: 'No matching advocates',
                    message: 'The directory only lists verified profiles registered with VIDHIK.',
                    icon: Icons.person_search_outlined,
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
                  itemCount: lawyers.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 9),
                  itemBuilder: (context, index) {
                    final lawyer = lawyers[index];
                    final specializations =
                        asMapList(lawyer['specializations_list'])
                            .map((e) => asString(e))
                            .where((e) => e.isNotEmpty)
                            .toList();
                    return AppCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              CircleAvatar(
                                radius: 22,
                                backgroundColor: AppColors.navy,
                                child: Text(
                                  initialsOf(
                                    firstNonEmpty([lawyer['full_name'], 'A']),
                                  ),
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 11),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            firstNonEmpty([
                                              lawyer['full_name'],
                                              'Advocate',
                                            ]),
                                            style: const TextStyle(
                                              fontWeight: FontWeight.w700,
                                              fontSize: 14,
                                            ),
                                          ),
                                        ),
                                        if (asBool(lawyer['is_verified'], true))
                                          const Tag(
                                            'Verified',
                                            color: AppColors.success,
                                          ),
                                      ],
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      firstNonEmpty([
                                        lawyer['specialization'],
                                        'General practice',
                                      ]),
                                      style: const TextStyle(
                                        fontSize: 11.5,
                                        color: AppColors.muted,
                                        height: 1.35,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 9),
                          Wrap(
                            spacing: 6,
                            runSpacing: 5,
                            children: [
                              if (lawyer['experience_years'] != null)
                                Tag(
                                  '${lawyer['experience_years']} yrs',
                                  color: AppColors.accent,
                                ),
                              if (asString(lawyer['city']).isNotEmpty)
                                Tag(
                                  asString(lawyer['city']),
                                  color: AppColors.info,
                                ),
                              if (asString(lawyer['court_practice']).isNotEmpty)
                                Tag(asString(lawyer['court_practice'])),
                              for (final specialization in specializations.take(
                                2,
                              ))
                                Tag(specialization, color: AppColors.muted),
                            ],
                          ),
                          if (asString(lawyer['bar_council_number'])
                              .isNotEmpty) ...[
                            const SizedBox(height: 8),
                            Text(
                              'Bar Council: ${lawyer['bar_council_number']}',
                              style: const TextStyle(
                                fontSize: 10.5,
                                color: AppColors.muted,
                              ),
                            ),
                          ],
                          const SizedBox(height: 10),
                          Row(
                            children: [
                              Expanded(
                                child: OutlinedButton.icon(
                                  onPressed: () => _launch(
                                    'tel',
                                    firstNonEmpty([lawyer['phone'], '']),
                                  ),
                                  icon: const Icon(Icons.call, size: 17),
                                  label: const Text('Call'),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: FilledButton.icon(
                                  onPressed: () => _launch(
                                    'mailto',
                                    firstNonEmpty([lawyer['email'], '']),
                                  ),
                                  icon: const Icon(
                                    Icons.mail_outline,
                                    size: 17,
                                  ),
                                  label: const Text('Email'),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
