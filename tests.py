from immich_duplicates import Asset


class TestAsset:

    def test_prefer_external_lib(self):
        a = Asset(
            {
                "originalPath": "/volume1/photo/Photos/2024-12-14 Christmas/IMG_4034.JPG"
            }
        )
        b = Asset(
            {
                "originalPath": "/usr/src/app/upload/upload/62989871-bc65-460b-ab33-84f6121b6777/f3/bb/f3bb0be3-cf9f-4258-9cee-6920e7acb752.JPG"
            }
        )
        assert a > b

    def test_both_in_external_lib(self):
        """
        if both are in the external library, prefer the one that is favorited (if
        any)
        """

        a = Asset(
            {
                "originalPath": "/volume1/photo/Photos/2024-12-14 Christmas/IMG_4034.JPG",
                "isFavorite": True,
            }
        )
        b = Asset(
            {
                "originalPath": "/volume1/photo/Photos/2023-11-11 Birthday/IMG_1234.JPG",
                "isFavorite": False,
            }
        )
        assert a > b
        
