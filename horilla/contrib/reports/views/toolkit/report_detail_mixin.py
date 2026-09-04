"""Data helpers for report detail views (pivots, aggregates, FK caching)."""

# Standard library imports
import logging

# Third-party imports (Django)
import pandas as pd

# Local imports
from ...utils import resolve_report_field
from .report_helper import create_temp_report_with_preview

logger = logging.getLogger(__name__)


class ReportDetailDataMixin:
    """Helper mixin with pivot/aggregate and chart helpers for report detail view."""

    def create_temp_report(self, original_report, preview_data):
        """Create a temporary Report used for front-end preview operations."""
        return create_temp_report_with_preview(original_report, preview_data)

    def get_configuration_type(self, report):
        """Return configuration type string based on row and column group counts."""
        row_count = len(report.row_groups_list)
        col_count = len(report.column_groups_list)
        return f"{row_count}_row_{col_count}_col"

    def get_verbose_name(self, field_name, model_class):
        """Get the verbose name of a field."""
        try:
            return resolve_report_field(model_class, field_name).verbose_name
        except Exception:
            return field_name.replace("__", " - ").title()

    def sort_pivot_table(self, context, sort_field, sort_direction):
        """Sort context["pivot_index"] (the ordered list of pivot row keys)
        by a clicked column: either the row label itself, or a value in
        pivot_table[row_key][sort_field] for any Count/aggregate column.
        Works for the flat 1-row pivot shapes (0/1/2 column groups); the
        hierarchical 2-row/3-row configs use a different data structure and
        are not sortable via this generic path.
        """
        pivot_index = context.get("pivot_index") or []
        pivot_table = context.get("pivot_table") or {}
        if not pivot_index:
            return

        row_header_names = {"__row__", "row", ""}
        sort_by_label = sort_field in row_header_names

        def sort_key(row_key):
            if sort_by_label:
                value = pivot_table.get(row_key, {}).get("_display", row_key)
            else:
                value = pivot_table.get(row_key, {}).get(sort_field)
            if isinstance(value, (int, float)):
                return (0, value, "")
            if value is None:
                return (1, 0, "")
            return (0, 0, str(value).lower())

        reverse = sort_direction == "desc"
        try:
            context["pivot_index"] = sorted(pivot_index, key=sort_key, reverse=reverse)
        except Exception as e:
            logger.error("Error sorting pivot table by %s: %s", sort_field, str(e))

    def handle_0_row_0_col(self, df, report, context, total_count=None):
        """Handle pivot configuration with 0 rows and 0 columns (simple aggregate / record count)."""
        try:
            record_count = total_count if total_count is not None else len(df)
            aggregate_columns = []
            if report.aggregate_columns_dict:
                for agg in report.aggregate_columns_dict:
                    aggregate_field = agg.get("field")
                    aggfunc = agg.get("aggfunc", "sum")
                    aggregate_column_name = f"{aggfunc.title()} of {self.get_verbose_name(aggregate_field, report.model_class)}"
                    if aggregate_field and not df.empty:
                        if aggfunc == "sum":
                            total_value = df[aggregate_field].sum()
                        elif aggfunc == "avg":
                            total_value = df[aggregate_field].mean()
                        elif aggfunc == "min":
                            total_value = df[aggregate_field].min()
                        elif aggfunc == "max":
                            total_value = df[aggregate_field].max()
                        elif aggfunc == "count":
                            total_value = record_count
                        else:
                            total_value = record_count
                        aggregate_columns.append(
                            {
                                "name": aggregate_column_name,
                                "function": aggfunc,
                                "value": total_value,
                                "field": aggregate_field,
                            }
                        )
                context["simple_aggregate"] = {
                    "field": (
                        aggregate_columns[0]["field"]
                        if aggregate_columns
                        else "Records"
                    ),
                    "value": (
                        aggregate_columns[0]["value"]
                        if aggregate_columns
                        else record_count
                    ),
                    "function": (
                        aggregate_columns[0]["function"]
                        if aggregate_columns
                        else "count"
                    ),
                }
            else:
                context["simple_aggregate"] = {
                    "field": "Records",
                    "value": record_count,
                    "function": "count",
                }
            context["aggregate_columns"] = aggregate_columns
        except Exception as e:
            context["error"] = f"Error in 0x0 configuration: {str(e)}"
            context["aggregate_columns"] = []

    def handle_1_row_0_col(self, df, report, context, fk_cache=None):
        """Build pivot data when there is 1 row group and 0 column groups (simple grouped counts and aggregates)."""
        try:
            if df.empty:
                context["pivot_index"] = []
                context["pivot_table"] = {}
                context["pivot_columns"] = ["Count"]
                context["aggregate_columns"] = []
                return

            model_class = report.model_class
            row_field = report.row_groups_list[0]

            groupby_obj = df.groupby(row_field)
            count_grouped = groupby_obj.size().to_dict()

            aggregate_functions = {}
            for agg in report.aggregate_columns_dict:
                aggregate_field = agg["field"]
                aggfunc = agg.get("aggfunc", "sum")
                if aggregate_field in df.columns:
                    if aggfunc == "sum":
                        aggregate_functions[aggregate_field] = (
                            "sum",
                            groupby_obj[aggregate_field].sum().to_dict(),
                        )
                    elif aggfunc == "avg":
                        aggregate_functions[aggregate_field] = (
                            "avg",
                            groupby_obj[aggregate_field].mean().to_dict(),
                        )
                    elif aggfunc == "min":
                        aggregate_functions[aggregate_field] = (
                            "min",
                            groupby_obj[aggregate_field].min().to_dict(),
                        )
                    elif aggfunc == "max":
                        aggregate_functions[aggregate_field] = (
                            "max",
                            groupby_obj[aggregate_field].max().to_dict(),
                        )
                    elif aggfunc == "count":
                        aggregate_functions[aggregate_field] = (
                            "count",
                            count_grouped,
                        )
                    else:
                        aggregate_functions[aggregate_field] = (
                            "count",
                            count_grouped,
                        )

            display_grouped = {}
            display_rows = []
            pivot_columns = ["Count"]

            aggregate_columns = []
            for agg in report.aggregate_columns_dict:
                aggregate_field = agg["field"]
                aggfunc = agg.get("aggfunc", "sum")
                aggregate_column_name = f"{aggfunc.title()} of {self.get_verbose_name(aggregate_field, model_class)}"
                pivot_columns.append(aggregate_column_name)

                if aggregate_field in aggregate_functions:
                    _, aggregate_data = aggregate_functions[aggregate_field]
                else:
                    aggregate_data = {}

                aggregate_columns.append(
                    {
                        "name": aggregate_column_name,
                        "function": aggfunc,
                        "field": aggregate_field,
                        "data": aggregate_data,
                    }
                )

            for row, count in count_grouped.items():
                display_info = self.get_display_value(
                    row, row_field, model_class, fk_cache
                )
                composite_key = display_info["composite_key"]
                display_grouped[composite_key] = {
                    "Count": count,
                    "_display": display_info["display"],
                    "_id": display_info["id"],
                }
                for agg in aggregate_columns:
                    display_grouped[composite_key][agg["name"]] = agg["data"].get(
                        row, 0
                    )
                display_rows.append(composite_key)

            context["pivot_index"] = display_rows
            context["pivot_table"] = display_grouped
            context["pivot_columns"] = pivot_columns
            context["aggregate_columns"] = aggregate_columns

        except Exception as e:
            context["error"] = f"Error in 1x0 configuration: {str(e)}"
            context["aggregate_columns"] = []

    def handle_1_row_1_col(self, df, report, context, fk_cache=None):
        """Build pivot table for configuration with 1 row group and 1 column group."""
        try:
            if df.empty:
                context["pivot_index"] = []
                context["pivot_table"] = {}
                context["pivot_columns"] = []
                context["aggregate_columns"] = []
                return

            model_class = report.model_class
            row_field = report.row_groups_list[0]
            col_field = report.column_groups_list[0]

            pivot_table = pd.pivot_table(
                df, index=[row_field], columns=[col_field], aggfunc="size", fill_value=0
            )

            pivot_dict = pivot_table.to_dict("index")
            transposed_dict = {}
            all_rows = pivot_table.index.tolist()
            all_columns = pivot_table.columns.tolist()

            row_display_cache = {}
            col_display_cache = {}
            for row in all_rows:
                row_display_cache[row] = self.get_display_value(
                    row, row_field, model_class, fk_cache
                )
            for col in all_columns:
                col_display_cache[col] = self.get_display_value(
                    col, col_field, model_class, fk_cache
                )

            display_rows = []
            display_columns = []
            for row in all_rows:
                display_info = row_display_cache[row]
                composite_key = display_info["composite_key"]
                display_rows.append(composite_key)
                transposed_dict[composite_key] = {
                    "total": 0,
                    "_display": display_info["display"],
                    "_id": display_info["id"],
                }
                for col in all_columns:
                    col_info = col_display_cache[col]
                    col_composite = col_info["composite_key"]
                    if col_composite not in display_columns:
                        display_columns.append(col_composite)
                    value = pivot_dict.get(row, {}).get(col, 0)
                    transposed_dict[composite_key][col_composite] = value
                    transposed_dict[composite_key]["total"] += value

            aggregate_columns = []
            groupby_obj = df.groupby(row_field)
            for agg in report.aggregate_columns_dict:
                aggregate_field = agg["field"]
                aggfunc = agg.get("aggfunc", "sum")
                aggregate_column_name = f"{aggfunc.title()} of {self.get_verbose_name(aggregate_field, model_class)}"

                if aggregate_field in df.columns:
                    if aggfunc == "sum":
                        aggregate_data = groupby_obj[aggregate_field].sum().to_dict()
                    elif aggfunc == "avg":
                        aggregate_data = groupby_obj[aggregate_field].mean().to_dict()
                    elif aggfunc == "min":
                        aggregate_data = groupby_obj[aggregate_field].min().to_dict()
                    elif aggfunc == "max":
                        aggregate_data = groupby_obj[aggregate_field].max().to_dict()
                    elif aggfunc == "count":
                        aggregate_data = groupby_obj.size().to_dict()
                    else:
                        aggregate_data = groupby_obj.size().to_dict()
                else:
                    aggregate_data = {}

                for row in all_rows:
                    display_info = row_display_cache[row]
                    composite_key = display_info["composite_key"]
                    transposed_dict[composite_key][aggregate_column_name] = (
                        aggregate_data.get(row, 0)
                    )
                display_columns.append(aggregate_column_name)
                aggregate_columns.append(
                    {
                        "name": aggregate_column_name,
                        "function": aggfunc,
                        "field": aggregate_field,
                    }
                )

            context["pivot_table"] = transposed_dict
            context["pivot_index"] = display_rows
            context["pivot_columns"] = display_columns
            context["aggregate_columns"] = aggregate_columns

        except Exception as e:
            context["error"] = f"Error in 1x1 configuration: {str(e)}"
            context["aggregate_columns"] = []

    def handle_1_row_2_col(self, df, report, context, fk_cache=None):
        """Build multi-level pivot table for 1 row group and 2 column groups."""
        try:
            if df.empty:
                context["pivot_index"] = []
                context["pivot_table"] = {}
                context["pivot_columns"] = []
                context["column_hierarchy"] = []
                context["aggregate_columns"] = []
                return

            model_class = report.model_class
            row_field = report.row_groups_list[0]
            col_field1 = report.column_groups_list[0]
            col_field2 = report.column_groups_list[1]

            pivot_table = pd.pivot_table(
                df,
                index=[row_field],
                columns=[col_field1, col_field2],
                aggfunc="size",
                fill_value=0,
            )

            pivot_dict = pivot_table.to_dict("index")
            transposed_dict = {}
            all_rows = pivot_table.index.tolist()
            column_hierarchy = []
            multi_level_columns = []

            for col_tuple in pivot_table.columns:
                col1_info = self.get_display_value(
                    col_tuple[0], col_field1, model_class
                )
                col2_info = self.get_display_value(
                    col_tuple[1], col_field2, model_class
                )
                col1_composite = col1_info["composite_key"]
                col2_composite = col2_info["composite_key"]
                column_key = f"{col1_composite}|{col2_composite}"
                multi_level_columns.append(column_key)
                column_hierarchy.append(
                    {
                        "level1": col1_composite,
                        "level1_display": col1_info["display"],
                        "level2": col2_composite,
                        "level2_display": col2_info["display"],
                        "key": column_key,
                    }
                )

            display_rows = []
            for row in all_rows:
                row_info = self.get_display_value(row, row_field, model_class)
                row_composite = row_info["composite_key"]
                display_rows.append(row_composite)
                transposed_dict[row_composite] = {
                    "total": 0,
                    "_display": row_info["display"],
                    "_id": row_info["id"],
                }
                for col_tuple in pivot_table.columns:
                    col1_info = self.get_display_value(
                        col_tuple[0], col_field1, model_class
                    )
                    col2_info = self.get_display_value(
                        col_tuple[1], col_field2, model_class
                    )
                    col1_composite = col1_info["composite_key"]
                    col2_composite = col2_info["composite_key"]
                    column_key = f"{col1_composite}|{col2_composite}"
                    value = pivot_dict.get(row, {}).get(col_tuple, 0)
                    transposed_dict[row_composite][column_key] = value
                    transposed_dict[row_composite]["total"] += value

            aggregate_columns = []
            for agg in report.aggregate_columns_dict:
                aggregate_field = agg["field"]
                aggfunc = agg.get("aggfunc", "sum")
                aggregate_column_name = f"{aggfunc.title()} of {self.get_verbose_name(aggregate_field, model_class)}"
                if aggfunc == "sum":
                    aggregate_data = (
                        df.groupby(row_field)[aggregate_field].sum().to_dict()
                    )
                elif aggfunc == "avg":
                    aggregate_data = (
                        df.groupby(row_field)[aggregate_field].mean().to_dict()
                    )
                elif aggfunc == "min":
                    aggregate_data = (
                        df.groupby(row_field)[aggregate_field].min().to_dict()
                    )
                elif aggfunc == "max":
                    aggregate_data = (
                        df.groupby(row_field)[aggregate_field].max().to_dict()
                    )
                elif aggfunc == "count":
                    aggregate_data = df.groupby(row_field).size().to_dict()
                else:
                    aggregate_data = df.groupby(row_field).size().to_dict()

                for row in all_rows:
                    row_info = self.get_display_value(row, row_field, model_class)
                    row_composite = row_info["composite_key"]
                    transposed_dict[row_composite][aggregate_column_name] = (
                        aggregate_data.get(row, 0)
                    )
                multi_level_columns.append(aggregate_column_name)
                column_hierarchy.append(
                    {
                        "level1": aggregate_column_name,
                        "level1_display": aggregate_column_name,
                        "level2": "",
                        "level2_display": "",
                        "key": aggregate_column_name,
                    }
                )
                aggregate_columns.append(
                    {
                        "name": aggregate_column_name,
                        "function": aggfunc,
                        "field": aggregate_field,
                    }
                )

            context["pivot_table"] = transposed_dict
            context["pivot_index"] = display_rows
            context["pivot_columns"] = multi_level_columns
            context["column_hierarchy"] = column_hierarchy
            context["aggregate_columns"] = aggregate_columns

        except Exception as e:
            context["error"] = f"Error in 1x2 configuration: {str(e)}"
            context["aggregate_columns"] = []

    def handle_2_row_0_col(self, df, report, context, fk_cache=None):
        """Build hierarchical data for configuration with 2 row groups and 0 columns."""
        try:
            if df.empty:
                context["hierarchical_data"] = {"groups": [], "grand_total": 0}
                context["aggregate_columns"] = []
                return

            hierarchical_data = []
            primary_group = report.row_groups_list[0]
            secondary_group = report.row_groups_list[1]
            model_class = report.model_class
            pivot_columns = ["Count"]

            primary_groups = df.groupby(primary_group)
            grand_total = 0

            # Compute aggregate columns
            aggregate_columns = []
            aggregate_data = {}
            for agg in report.aggregate_columns_dict:
                aggregate_field = agg["field"]
                aggfunc = agg.get("aggfunc", "sum")
                aggregate_column_name = f"{aggfunc.title()} of {self.get_verbose_name(aggregate_field, model_class)}"
                pivot_columns.append(aggregate_column_name)
                if aggfunc == "sum":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([primary_group, secondary_group])[aggregate_field]
                        .sum()
                        .to_dict()
                    )
                elif aggfunc == "avg":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([primary_group, secondary_group])[aggregate_field]
                        .mean()
                        .to_dict()
                    )
                elif aggfunc == "min":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([primary_group, secondary_group])[aggregate_field]
                        .min()
                        .to_dict()
                    )
                elif aggfunc == "max":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([primary_group, secondary_group])[aggregate_field]
                        .max()
                        .to_dict()
                    )
                elif aggfunc == "count":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([primary_group, secondary_group]).size().to_dict()
                    )
                else:
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([primary_group, secondary_group]).size().to_dict()
                    )
                aggregate_columns.append(
                    {
                        "name": aggregate_column_name,
                        "function": aggfunc,
                        "field": aggregate_field,
                    }
                )

            for primary_value, primary_df in primary_groups:
                primary_info = self.get_display_value(
                    primary_value, primary_group, model_class
                )
                primary_composite = primary_info["composite_key"]
                group_data = {
                    "primary_group": primary_composite,
                    "primary_group_display": primary_info["display"],
                    "primary_group_id": primary_info["id"],
                    "items": [],
                    "subtotal": 0,
                }

                # Group by secondary group within primary group
                secondary_groups = primary_df.groupby(secondary_group)
                for secondary_value, secondary_df in secondary_groups:
                    secondary_info = self.get_display_value(
                        secondary_value, secondary_group, model_class
                    )
                    secondary_composite = secondary_info["composite_key"]
                    count_value = len(secondary_df)
                    item_data = {
                        "secondary_group": secondary_composite,
                        "secondary_group_display": secondary_info["display"],
                        "secondary_group_id": secondary_info["id"],
                        "values": {"Count": count_value},
                        "total": count_value,
                    }
                    for agg in aggregate_columns:
                        key = (primary_value, secondary_value)
                        item_data["values"][agg["name"]] = aggregate_data[
                            agg["name"]
                        ].get(key, 0)
                    group_data["items"].append(item_data)
                    group_data["subtotal"] += count_value

                hierarchical_data.append(group_data)
                grand_total += group_data["subtotal"]

            context["hierarchical_data"] = {
                "groups": hierarchical_data,
                "grand_total": grand_total,
            }
            context["pivot_columns"] = pivot_columns
            context["aggregate_columns"] = aggregate_columns

        except Exception as e:
            context["error"] = f"Error in 2x0 configuration: {str(e)}"
            context["aggregate_columns"] = []

    def handle_2_row_1_col(self, df, report, context, fk_cache=None):
        """Build hierarchical data for configuration with 2 row groups and 1 column group."""
        try:
            if df.empty:
                context["hierarchical_data"] = {"groups": [], "grand_total": 0}
                context["pivot_columns"] = []
                context["aggregate_columns"] = []
                return

            model_class = report.model_class
            primary_group = report.row_groups_list[0]
            secondary_group = report.row_groups_list[1]
            col_field = report.column_groups_list[0]

            # Get unique column values for headers
            unique_cols = df[col_field].unique().tolist()
            display_cols = []
            col_mapping = {}
            for col in unique_cols:
                col_info = self.get_display_value(col, col_field, model_class)
                col_composite = col_info["composite_key"]
                display_cols.append(col_composite)
                col_mapping[col] = col_composite

            # Compute aggregate columns
            aggregate_columns = []
            aggregate_data = {}
            for agg in report.aggregate_columns_dict:
                aggregate_field = agg["field"]
                aggfunc = agg.get("aggfunc", "sum")
                aggregate_column_name = f"{aggfunc.title()} of {self.get_verbose_name(aggregate_field, model_class)}"
                display_cols.append(aggregate_column_name)
                if aggfunc == "sum":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([primary_group, secondary_group])[aggregate_field]
                        .sum()
                        .to_dict()
                    )
                elif aggfunc == "avg":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([primary_group, secondary_group])[aggregate_field]
                        .mean()
                        .to_dict()
                    )
                elif aggfunc == "min":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([primary_group, secondary_group])[aggregate_field]
                        .min()
                        .to_dict()
                    )
                elif aggfunc == "max":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([primary_group, secondary_group])[aggregate_field]
                        .max()
                        .to_dict()
                    )
                elif aggfunc == "count":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([primary_group, secondary_group]).size().to_dict()
                    )
                else:
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([primary_group, secondary_group]).size().to_dict()
                    )
                aggregate_columns.append(
                    {
                        "name": aggregate_column_name,
                        "function": aggfunc,
                        "field": aggregate_field,
                    }
                )

            hierarchical_data = []
            primary_groups = df.groupby(primary_group)
            grand_total = 0

            for primary_value, primary_df in primary_groups:
                primary_info = self.get_display_value(
                    primary_value, primary_group, model_class
                )
                primary_composite = primary_info["composite_key"]
                group_data = {
                    "primary_group": primary_composite,
                    "primary_group_display": primary_info["display"],
                    "primary_group_id": primary_info["id"],
                    "items": [],
                    "subtotal": 0,
                }

                secondary_groups = primary_df.groupby(secondary_group)
                for secondary_value, secondary_df in secondary_groups:
                    secondary_info = self.get_display_value(
                        secondary_value, secondary_group, model_class
                    )
                    secondary_composite = secondary_info["composite_key"]
                    item_data = {
                        "secondary_group": secondary_composite,
                        "secondary_group_display": secondary_info["display"],
                        "secondary_group_id": secondary_info["id"],
                        "values": {},
                        "total": 0,
                    }

                    # Compute counts for column groups
                    for col_value in unique_cols:
                        col_composite = col_mapping[col_value]
                        filtered_df = secondary_df[secondary_df[col_field] == col_value]
                        value = len(filtered_df)
                        item_data["values"][col_composite] = value
                        item_data["total"] += value

                    # Add aggregate values
                    for agg in aggregate_columns:
                        key = (primary_value, secondary_value)
                        item_data["values"][agg["name"]] = aggregate_data[
                            agg["name"]
                        ].get(key, 0)

                    group_data["items"].append(item_data)
                    group_data["subtotal"] += item_data["total"]

                hierarchical_data.append(group_data)
                grand_total += group_data["subtotal"]

            context["hierarchical_data"] = {
                "groups": hierarchical_data,
                "grand_total": grand_total,
            }
            context["pivot_columns"] = display_cols
            context["aggregate_columns"] = aggregate_columns

        except Exception as e:
            context["error"] = f"Error in 2x1 configuration: {str(e)}"
            context["aggregate_columns"] = []

    def handle_3_row_0_col(self, df, report, context, fk_cache=None):
        """Handle pivot formatting for configuration with 3 rows and 0 columns."""
        try:
            if df.empty:
                context["three_level_data"] = {"groups": [], "grand_total": 0}
                context["aggregate_columns"] = []
                return

            model_class = report.model_class
            level1_field = report.row_groups_list[0]
            level2_field = report.row_groups_list[1]
            level3_field = report.row_groups_list[2]

            three_level_data = []
            grand_total = 0

            # Compute aggregate columns
            aggregate_columns = []
            aggregate_data = {}
            for agg in report.aggregate_columns_dict:
                aggregate_field = agg["field"]
                aggfunc = agg.get("aggfunc", "sum")
                aggregate_column_name = f"{aggfunc.title()} of {self.get_verbose_name(aggregate_field, model_class)}"
                if aggfunc == "sum":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([level1_field, level2_field, level3_field])[
                            aggregate_field
                        ]
                        .sum()
                        .to_dict()
                    )
                elif aggfunc == "avg":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([level1_field, level2_field, level3_field])[
                            aggregate_field
                        ]
                        .mean()
                        .to_dict()
                    )
                elif aggfunc == "min":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([level1_field, level2_field, level3_field])[
                            aggregate_field
                        ]
                        .min()
                        .to_dict()
                    )
                elif aggfunc == "max":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([level1_field, level2_field, level3_field])[
                            aggregate_field
                        ]
                        .max()
                        .to_dict()
                    )
                elif aggfunc == "count":
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([level1_field, level2_field, level3_field])
                        .size()
                        .to_dict()
                    )
                else:
                    aggregate_data[aggregate_column_name] = (
                        df.groupby([level1_field, level2_field, level3_field])
                        .size()
                        .to_dict()
                    )
                aggregate_columns.append(
                    {
                        "name": aggregate_column_name,
                        "function": aggfunc,
                        "field": aggregate_field,
                    }
                )

            level1_groups = df.groupby(level1_field)
            for level1_value, level1_df in level1_groups:
                level1_info = self.get_display_value(
                    level1_value, level1_field, model_class
                )
                level1_composite = level1_info["composite_key"]
                level1_data = {
                    "level1_group": level1_composite,
                    "level1_group_display": level1_info["display"],
                    "level1_group_id": level1_info["id"],
                    "level2_groups": [],
                    "level1_total": 0,
                }

                level2_groups = level1_df.groupby(level2_field)
                for level2_value, level2_df in level2_groups:
                    level2_info = self.get_display_value(
                        level2_value, level2_field, model_class
                    )
                    level2_composite = level2_info["composite_key"]
                    level2_data = {
                        "level2_group": level2_composite,
                        "level2_group_display": level2_info["display"],
                        "level2_group_id": level2_info["id"],
                        "level3_items": [],
                        "level2_total": 0,
                    }

                    level3_groups = level2_df.groupby(level3_field)
                    for level3_value, level3_df in level3_groups:
                        level3_info = self.get_display_value(
                            level3_value, level3_field, model_class
                        )
                        level3_composite = level3_info["composite_key"]
                        count_value = len(level3_df)
                        aggregate_values = {
                            agg["name"]: aggregate_data[agg["name"]].get(
                                (level1_value, level2_value, level3_value), 0
                            )
                            for agg in aggregate_columns
                        }

                        level3_item = {
                            "level3_group": level3_composite,
                            "level3_group_display": level3_info["display"],
                            "level3_group_id": level3_info["id"],
                            "count": count_value,
                            "aggregate_values": aggregate_values,
                        }

                        level2_data["level3_items"].append(level3_item)
                        level2_data["level2_total"] += count_value

                    level1_data["level2_groups"].append(level2_data)
                    level1_data["level1_total"] += level2_data["level2_total"]

                three_level_data.append(level1_data)
                grand_total += level1_data["level1_total"]

            context["three_level_data"] = {
                "groups": three_level_data,
                "grand_total": grand_total,
            }
            context["aggregate_columns"] = aggregate_columns

        except Exception as e:
            context["error"] = f"Error in 3x0 configuration: {str(e)}"
            context["aggregate_columns"] = []

    def _batch_load_foreign_keys(self, df, model_class, fields_list):
        """Batch load all foreign key values at once to avoid N+1 queries."""
        fk_cache = {}
        for field_name in fields_list:
            try:
                field = resolve_report_field(model_class, field_name)
                if (
                    hasattr(field, "related_model")
                    and field.related_model
                    and field_name in df.columns
                ):
                    unique_values = df[field_name].dropna().unique()
                    if len(unique_values) > 0:
                        related_objects = field.related_model.objects.filter(
                            pk__in=unique_values
                        )
                        fk_cache[field_name] = {obj.pk: obj for obj in related_objects}
            except Exception:
                pass
        return fk_cache

    def get_display_value(self, value, field_name, model_class, fk_cache=None):
        """Return a dict with display text, id and composite_key for a given field value and model.

        Optimized to use pre-loaded cache to avoid N+1 queries.
        """
        try:
            field = resolve_report_field(model_class, field_name)
            if hasattr(field, "related_model") and field.related_model:
                if fk_cache and field_name in fk_cache:
                    related_obj = fk_cache[field_name].get(value)
                    if related_obj:
                        return {
                            "display": str(related_obj),
                            "id": related_obj.pk,
                            "composite_key": f"{str(related_obj)}||{related_obj.pk}",
                        }
                    return {
                        "display": f"Unknown ({value})",
                        "id": value,
                        "composite_key": f"Unknown ({value})",
                    }
                try:
                    related_obj = field.related_model.objects.get(pk=value)
                    return {
                        "display": str(related_obj),
                        "id": related_obj.pk,
                        "composite_key": f"{str(related_obj)}||{related_obj.pk}",
                    }
                except field.related_model.DoesNotExist:
                    return {
                        "display": f"Unknown ({value})",
                        "id": value,
                        "composite_key": f"Unknown ({value})",
                    }
            if hasattr(field, "choices") and field.choices:
                choice_dict = dict(field.choices)
                display = choice_dict.get(value, value)
                return {"display": display, "id": value, "composite_key": str(display)}
            if value is None or value == "":
                return {
                    "display": "Unspecified (-)",
                    "id": None,
                    "composite_key": "Unspecified (-)",
                }
            return {"display": str(value), "id": value, "composite_key": str(value)}
        except Exception:
            return {
                "display": str(value) if value is not None else "Unspecified (-)",
                "id": value,
                "composite_key": str(value) if value is not None else "Unspecified (-)",
            }
