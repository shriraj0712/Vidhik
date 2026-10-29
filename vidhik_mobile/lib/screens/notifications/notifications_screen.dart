import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme/app_theme.dart';
import '../../core/utils/format.dart';
import '../../models/citizen.dart';
import '../../services/api_service.dart';
import '../../widgets/common.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  late Future<Map<String, dynamic>> _future;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _future = context.read<ApiService>().notifications();
  }

  Future<void> _reload() async {
    setState(() {
      _future = context.read<ApiService>().notifications();
    });
    await _future;
  }

  Future<void> _markAll() async {
    setState(() {
      _busy = true;
    });
    try {
      await context.read<ApiService>().markAllNotificationsRead();
      if (!mounted) return;
      await _reload();
      if (mounted) showInfoSnack(context, 'All notifications marked as read.');
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  Future<void> _markRead(CitizenNotification notification) async {
    if (notification.isRead) return;
    try {
      await context.read<ApiService>().markNotificationRead(
        notification.notificationId,
      );
      await _reload();
    } on Exception catch (e) {
      if (mounted) showErrorSnack(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          TextButton(
            onPressed: _busy ? null : _markAll,
            child: const Text(
              'Mark all read',
              style: TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: AsyncView<Map<String, dynamic>>(
          future: _future,
          onRetry: _reload,
          loadingText: 'Loading alerts…',
          builder: (context, data) {
            final items = asMapList(data['notifications'])
                .map(CitizenNotification.fromJson)
                .toList();
            final unread = asInt(data['unread_count']);
            if (items.isEmpty) {
              return const EmptyState(
                title: 'No notifications',
                message: 'Hearing reminders, procedural milestones and case activity will appear here.',
                icon: Icons.notifications_none,
              );
            }
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.teal.withValues(alpha: 0.07),
                    borderRadius: BorderRadius.circular(11),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.mark_email_unread_outlined,
                        size: 18,
                        color: AppColors.teal,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '$unread unread · ${items.length} total',
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.teal,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                for (final item in items)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: AppCard(
                      onTap: () => _markRead(item),
                      color: item.isRead
                          ? null
                          : AppColors.teal.withValues(alpha: 0.035),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color:
                                  (item.isRead
                                          ? AppColors.muted
                                          : AppColors.teal)
                                      .withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(9),
                            ),
                            child: Icon(
                              item.notificationType == 'hearing'
                                  ? Icons.event
                                  : Icons.notifications_active_outlined,
                              size: 17,
                              color: item.isRead
                                  ? AppColors.muted
                                  : AppColors.teal,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        item.title,
                                        style: TextStyle(
                                          fontWeight: item.isRead
                                              ? FontWeight.w500
                                              : FontWeight.w700,
                                          fontSize: 13.5,
                                        ),
                                      ),
                                    ),
                                    if (!item.isRead)
                                      Container(
                                        width: 7,
                                        height: 7,
                                        decoration: const BoxDecoration(
                                          color: AppColors.teal,
                                          shape: BoxShape.circle,
                                        ),
                                      ),
                                  ],
                                ),
                                const SizedBox(height: 3),
                                Text(
                                  item.message,
                                  style: const TextStyle(
                                    fontSize: 12.5,
                                    height: 1.4,
                                  ),
                                ),
                                const SizedBox(height: 5),
                                Text(
                                  formatDateTime(item.createdAt),
                                  style: const TextStyle(
                                    fontSize: 10.5,
                                    color: AppColors.muted,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}
