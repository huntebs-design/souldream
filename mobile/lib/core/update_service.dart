import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api_client.dart';
import 'models.dart';

class UpdateStatus {
  const UpdateStatus({required this.release, required this.currentBuild});

  final MobileRelease release;
  final int currentBuild;

  bool get updateAvailable => release.latestBuild > currentBuild;
  bool get updateRequired => release.minimumBuild > currentBuild;
}

class UpdateService {
  UpdateService(this.api);

  final ApiClient api;

  Future<UpdateStatus> check() async {
    final package = await PackageInfo.fromPlatform();
    return UpdateStatus(
      release: await api.getMobileRelease(),
      currentBuild: int.tryParse(package.buildNumber) ?? 1,
    );
  }

  Future<void> openDownload(String url) async {
    final uri = Uri.tryParse(url);
    if (uri == null ||
        !await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      throw const ApiException('The update download could not be opened.');
    }
  }
}
