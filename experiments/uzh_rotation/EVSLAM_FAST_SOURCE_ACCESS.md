# EvSLAM fast source access: bounded follow-up to external quota obstruction

The EvSLAM original GT recordings for drone_rot_norm and drone_rot_fast yielded independently verified ~3.99 and ~6.00 projected body-Y turns in [Actions 39933938407](https://github.com/metalogiclabs/mathgraph/actions/runs/39933938407). Their raw sensor bags were NOT acquired in that experiment.

The original author download-page IDs are norm `1NNUZgkzpyR321AFeI1j5Uv2DKV8E_W3u` and fast `1t4viDrRV40_uOS3Tfh9-jMbGKgHorTI1`. Drive metadata returned norm 6,104,603,846 and fast 6,551,527,649 bytes. Anonymous gdown attempt for norm in [failed Actions 39934255115](https://github.com/metalogiclabs/mathgraph/actions/runs/39934255115) was blocked by "Too many users" quota before data download. Authenticated connector also refused original 6.10GB due to 268,435,456-byte transfer cap.

This source-distinct fast access attempt uses the pre-identified author file ID, size and exactly one gdown request. If the publisher's transfer fails, record `UNKNOWN_PUBLISHER_DOWNLOAD_QUOTA` or another explicit transfer obstruction as the result, with no invented SHA256 or event/IMU measurements. If successful, verify exact metadata file size, SHA256 source identity, original bag structure and topics before reading event/IMU values. This is only original-source access and never a heading estimation or proof-of-flight result.

A quota failure is an external blocker, not a code failure to be "repaired" by weakening source requirements or substituting another file.
