"""Helper module for the EDL case study."""

import json

atmospheric_v_entry = 20000.0
atmospheric_v_exit = 1600.0

atmospheric_t_entry = 0
atmospheric_t_exit = 90.0

skycrane_v_entry = 2.7
skycrane_v_exit = 0

skycrane_t_entry = 398.0
skycrane_t_exit = 410.0

# For converting large images to base64, use: https://www.base64encoder.io/image-to-base64-converter/
# The strings below correspond to "Base64 Encoded String"

# The format for the inline figures as follows:
#
# variable=""  # noqa: E501

with open("images.json") as f:
    file_data = json.load(f)

figure_m2020_edl_timeline_segmented = file_data["figure_m2020_edl_timeline_segmented"]
figure_segment_contracts_page1 = file_data["figure_segment_contracts_page1"]
figure_segment_contracts_page2 = file_data["figure_segment_contracts_page2"]
figure_segment_contracts_page3 = file_data["figure_segment_contracts_page3"]