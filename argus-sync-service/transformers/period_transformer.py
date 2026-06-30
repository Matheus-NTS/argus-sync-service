import pandas as pd


class PeriodTransformer:

    def filter_by_month(self, dataframe, date_column, month, year):

        df = dataframe.copy()

        df[date_column] = pd.to_datetime(df[date_column])

        return df[
            (df[date_column].dt.month == month) &
            (df[date_column].dt.year == year)
        ]

    def filter_by_year(self, dataframe, date_column, year):

        df = dataframe.copy()

        df[date_column] = pd.to_datetime(df[date_column])

        return df[
            df[date_column].dt.year == year
        ]