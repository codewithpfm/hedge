from blocks.enums import RESAMPLE_TF
from functools import cache


# ReSampler
class Resample:
    def __init__(self, data):
        self.data = data.dropna()

    def __resampler(self, freq):
        tf = f"{freq} Min" if type(freq) is int else freq

        resampled = self.data.resample(tf).agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }
        )

        return resampled.dropna()

    @property
    def original(self):
        return self.data

    @property
    @cache
    def M1(self):
        return self.__resampler(RESAMPLE_TF("1M"))

    @property
    @cache
    def M5(self):
        return self.__resampler(RESAMPLE_TF("5M"))

    @property
    def M8(self):
        return self.__resampler(RESAMPLE_TF("8M"))

    @property
    @cache
    def M15(self):
        return self.__resampler(RESAMPLE_TF("15M"))

    @property
    @cache
    def M30(self):
        return self.__resampler(RESAMPLE_TF("30M"))

    @property
    @cache
    def H1(self):
        return self.__resampler(RESAMPLE_TF("1H"))

    @property
    @cache
    def H4(self):
        return self.__resampler(RESAMPLE_TF("4H"))

    @property
    @cache
    def D1(self):
        return self.__resampler(RESAMPLE_TF("1D"))

    @property
    @cache
    def W1(self):
        return self.__resampler(RESAMPLE_TF("1W"))

    @property
    @cache
    def M(self):
        return self.__resampler(RESAMPLE_TF("M"))

    @property
    @cache
    def Q(self):
        return self.__resampler(RESAMPLE_TF("Q"))

    @property
    @cache
    def Y(self):
        return self.__resampler(RESAMPLE_TF("Y"))

    @cache
    def getX(self, X: int):
        return self.__resampler(X)

    @cache
    def get(self, tf: str):
        return self.__resampler(RESAMPLE_TF(tf))
