class GoalMetrics:
    def __init__(self, base_column="valor", super_percent=0.24, hyper_percent=0.37):
        self.base_column = base_column
        self.super_percent = super_percent
        self.hyper_percent = hyper_percent

    def add_goal_levels(self, metas_df):
        metas = metas_df.copy()

        metas["meta_base"] = metas[self.base_column]
        metas["super_meta"] = metas["meta_base"] * (1 + self.super_percent)
        metas["hiper_meta"] = metas["meta_base"] * (1 + self.hyper_percent)

        return metas