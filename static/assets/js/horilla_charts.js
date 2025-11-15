/**
 * ECharts Configuration Module - FIXED VERSION
 * Handles all chart types and configurations for the reporting system
 * Fixed legend issue for column, bar, line, and scatter charts
 */

var EChartsConfig = {

    // Default colors palette
    defaultColors: [
        '#a5b4fc', '#fca5a5', '#fdba74', '#38bdf8', '#a7f3d0',
        '#c084fc', '#fb7185', '#60a5fa', '#5eead4', '#22d3ee',
        '#f8b4cb', '#b4d8ff', '#c7d2fe', '#fde68a',
        '#d1d5db', '#e879f9', '#94a3b8', '#fcd34d',
        '#86efac', '#f472b6', '#818cf8', '#fb923c',
        '#a78bfa', '#4ade80', '#f59e0b', '#ec4899', '#06b6d4'
    ],

    // Common styling configuration
    commonStyles: {
        fontFamily: "'Inter', sans-serif",
        fontSize: 12,
        legendFontSize: 12,
        axisFontSize: 11
    },

    // Get chart option based on configuration
    getChartOption: function(config) {
        const { type, labels, data, colors, labelField, stackedData, hasMultipleGroups, urls } = config;
        const chartColors = colors && colors.length > 0 ? colors : this.defaultColors;

        this._currentUrls = urls || [];

        switch (type.toLowerCase()) {
            case 'pie':
                return this.getPieChartOption(labels, data, chartColors, labelField, urls);
            case 'donut':
                return this.getDonutChartOption(labels, data, chartColors, labelField, urls);
            case 'bar':
                return this.getBarChartOption(labels, data, chartColors, labelField, urls);
            case 'column':
                return this.getColumnChartOption(labels, data, chartColors, labelField, urls);
            case 'line':
                return this.getLineChartOption(labels, data, chartColors, labelField, urls);
            case 'funnel':
                return this.getFunnelChartOption(labels, data, chartColors, labelField, urls);
            case 'scatter':
                return this.getScatterChartOption(labels, data, chartColors, labelField, urls);
            case 'stacked_vertical':
                return hasMultipleGroups ?
                    this.getStackedVerticalChartOption(stackedData, chartColors, labelField, urls) :
                    this.getColumnChartOption(labels, data, chartColors, labelField, urls);
            case 'stacked_horizontal':
                return hasMultipleGroups ?
                    this.getStackedHorizontalChartOption(stackedData, chartColors, labelField, urls) :
                    this.getBarChartOption(labels, data, chartColors, labelField, urls);
            default:
                return this.getPieChartOption(labels, data, chartColors, labelField, urls);
        }
    },

    // Common legend configuration
    getLegendConfig: function(position = 'bottom') {
        return {
            orient: position === 'bottom' ? 'horizontal' : 'vertical',
            bottom: position === 'bottom' ? '0%' : undefined,
            left: position === 'bottom' ? 'center' : '0%',
            top: position === 'left' ? 'center' : undefined,
            itemWidth: 12,
            itemHeight: 12,
            textStyle: {
                fontSize: this.commonStyles.legendFontSize,
                fontFamily: this.commonStyles.fontFamily
            }
        };
    },

    // Common grid configuration for bar/column charts
    getGridConfig: function() {
        return {
            left: '3%',
            right: '4%',
            bottom: '15%',
            top: '10%',
            containLabel: true
        };
    },

    // Pie Chart Configuration
    getPieChartOption: function(labels, data, colors, labelField, urls) {
        const pieData = labels.map((label, index) => ({
            name: label,
            value: data[index] || 0,
            url: urls && urls[index] ? urls[index] : null
        }));

        return {
            ...this.getAnimationConfig(),
            tooltip: {
                trigger: 'item',
                formatter: function(params) {
                    const hasUrl = params.data.url && params.data.url !== '#';
                    return `${params.seriesName}<br/>${params.name}: ${params.value} (${params.percent}%)${hasUrl ? '<br/><i>Click to view details</i>' : ''}`;
                }
            },
            // tooltip: {
            //     trigger: 'item',
            //     formatter: '{a} <br/>{b}: {c} ({d}%)'
            // },
            legend: this.getLegendConfig(),
            color: colors,
            series: [{
                name: labelField,
                type: 'pie',
                radius: '65%',
                center: ['50%', '45%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 4,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: false
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 14,
                        fontWeight: 'bold'
                    },
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                },
                labelLine: {
                    show: false
                },
                data: pieData
            }]
        };
    },

    // Donut Chart Configuration
    getDonutChartOption: function(labels, data, colors, labelField, urls) {
        const pieData = labels.map((label, index) => ({
            name: label,
            value: data[index] || 0,
            url: urls && urls[index] ? urls[index] : null
        }));

        return {
            ...this.getAnimationConfig(),
            tooltip: {
                trigger: 'item',
                formatter: function(params) {
                    const hasUrl = params.data.url && params.data.url !== '#';
                    return `${params.seriesName}<br/>${params.name}: ${params.value} (${params.percent}%)${hasUrl ? '<br/><i style="color: #999; font-size: 11px;">Click to view details</i>' : ''}`;
                }
            },
            legend: this.getLegendConfig(),
            color: colors,
            series: [{
                name: labelField,
                type: 'pie',
                radius: ['40%', '70%'],
                center: ['50%', '45%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: false
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 14,
                        fontWeight: 'bold'
                    },
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                },
                labelLine: {
                    show: false
                },
                data: pieData
            }]
        };
    },

    // FIXED: Column Chart (Vertical) Configuration - Multiple Series
    getColumnChartOption: function(labels, data, colors, labelField, urls) {
        // Create individual series for each category to show proper legends
        const series = labels.map((label, index) => ({
            name: label,
            type: 'bar',
            data: [data[index] || 0],
            itemStyle: {
                color: colors[index % colors.length],
                borderRadius: [4, 4, 0, 0]
            }
        }));

        return {
            ...this.getAnimationConfig(),
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                },
                formatter: function(params) {
                    let tooltip = '';
                    params.forEach(param => {
                        if (param.value > 0) {
                            tooltip += `${param.marker} ${param.seriesName}: ${param.value}<br/>`;
                        }
                    });
                    if (urls && urls.length > 0) {
                        tooltip += '<i style="color: #999; font-size: 11px;">Click to view details</i>';
                    }
                    return tooltip;
                }
            },
            legend: {
                ...this.getLegendConfig(),
                show: true,
                type: 'scroll'
            },
            grid: this.getGridConfig(),
            xAxis: {
                type: 'category',
                data: [labelField], // Single category for all bars
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily
                }
            },
            color: colors,
            series: series
        };
    },

    // FIXED: Bar Chart (Horizontal) Configuration - Multiple Series
    getBarChartOption: function(labels, data, colors, labelField, urls) {
        // Create individual series for each category to show proper legends
        const series = labels.map((label, index) => ({
            name: label,
            type: 'bar',
            data: [data[index] || 0],
            itemStyle: {
                color: colors[index % colors.length],
                borderRadius: [0, 4, 4, 0]
            }
        }));

        return {
            ...this.getAnimationConfig(),
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                },
                formatter: function(params) {
                    let tooltip = '';
                    params.forEach(param => {
                        if (param.value > 0) {
                            tooltip += `${param.marker} ${param.seriesName}: ${param.value}<br/>`;
                        }
                    });
                    if (urls && urls.length > 0) {
                        tooltip += '<i style="color: #999; font-size: 11px;">Click to view details</i>';
                    }
                    return tooltip;
                }
            },
            legend: {
                ...this.getLegendConfig(),
                show: true,
                type: 'scroll'
            },
            grid: this.getGridConfig(),
            xAxis: {
                type: 'value',
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily
                }
            },
            yAxis: {
                type: 'category',
                data: [labelField], // Single category for all bars
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily
                }
            },
            color: colors,
            series: series
        };
    },

    // FIXED: Line Chart Configuration - Multiple Series
    getLineChartOption: function(labels, data, colors, labelField, urls) {
        // For line chart, we need a different approach - use labels as x-axis
        const lineData = data.map((value, index) => ({
            value: value,
            url: urls && urls[index] ? urls[index] : null
        }));

        return {
            ...this.getAnimationConfig(),
            tooltip: {
                trigger: 'axis',
                formatter: function(params) {
                    let tooltip = `<strong>${params[0].axisValue}</strong><br/>`;
                    params.forEach(param => {
                        const hasUrl = param.data.url && param.data.url !== '#';
                        tooltip += `${param.marker} ${param.seriesName}: ${param.data.value}${hasUrl ? '<br/><i style="color: #999; font-size: 11px;">Click to view details</i>' : ''}<br/>`;
                    });
                    return tooltip;
                }
            },
            legend: {
                ...this.getLegendConfig(),
                show: true
            },
            grid: this.getGridConfig(),
            xAxis: {
                type: 'category',
                data: labels,
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily,
                    rotate: labels.some(label => label.length > 8) ? 45 : 0
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily
                }
            },
            color: colors,
            series: [{
                name: labelField,
                type: 'line',
                data: data,
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                lineStyle: {
                    width: 3
                },
                areaStyle: {
                    opacity: 0.1
                }
            }]
        };
    },

    // Funnel Chart Configuration
    getFunnelChartOption: function(labels, data, colors, labelField,urls) {
        const funnelData = labels.map((label, index) => ({
            name: label,
            value: data[index] || 0,
            url: urls && urls[index] ? urls[index] : null
        }));

        return {
            ...this.getAnimationConfig(),
            tooltip: {
                trigger: 'item',
                formatter: function(params) {
                    const hasUrl = params.data.url && params.data.url !== '#';
                    return `${params.seriesName}<br/>${params.name}: ${params.value}${hasUrl ? '<br/><i>Click to view details</i>' : ''}`;
                }
            },
            // ...this.getAnimationConfig(),
            // tooltip: {
            //     trigger: 'item',
            //     formatter: '{a} <br/>{b}: {c}'
            // },
            legend: this.getLegendConfig(),
            color: colors,
            series: [{
                name: labelField,
                type: 'funnel',
                left: '10%',
                top: '5%',
                width: '80%',
                height: '70%',
                min: 0,
                max: Math.max(...data),
                minSize: '0%',
                maxSize: '100%',
                sort: 'descending',
                gap: 2,
                label: {
                    show: true,
                    position: 'inside',
                    fontSize: 12,
                    fontFamily: this.commonStyles.fontFamily
                },
                labelLine: {
                    length: 10,
                    lineStyle: {
                        width: 1,
                        type: 'solid'
                    }
                },
                itemStyle: {
                    borderColor: '#fff',
                    borderWidth: 1
                },
                emphasis: {
                    label: {
                        fontSize: 14
                    }
                },
                data: funnelData
            }]
        };
    },

    // FIXED: Scatter Chart Configuration - Multiple Series
    getScatterChartOption: function(labels, data, colors, labelField, urls) {
        // Create individual series for each data point to show proper legends
        const series = labels.map((label, index) => ({
            name: label,
            type: 'scatter',
            data: [[index, data[index] || 0]],
            symbolSize: function(data) {
                return Math.sqrt(data[1]) * 2 + 10;
            },
            itemStyle: {
                color: colors[index % colors.length],
                opacity: 0.8
            },
            emphasis: {
                focus: 'series',
                itemStyle: {
                    opacity: 1
                }
            }
        }));

        return {
            ...this.getAnimationConfig(),
            tooltip: {
                trigger: 'item',
                formatter: function(params) {
                    const hasUrl = params.data[2] && params.data[2] !== '#';
                    return `${params.seriesName}: ${params.data[1]}${hasUrl ? '<br/><i style="color: #999; font-size: 11px;">Click to view details</i>' : ''}`;
                }
            },
            legend: {
                ...this.getLegendConfig(),
                show: true,
                type: 'scroll'
            },
            grid: this.getGridConfig(),
            xAxis: {
                type: 'category',
                data: labels,
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily,
                    rotate: labels.some(label => label.length > 8) ? 45 : 0
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily
                }
            },
            color: colors,
            series: series
        };
    },

    // Stacked Vertical Chart Configuration
    getStackedVerticalChartOption: function(stackedData, colors, labelField, urls) {
        if (!stackedData || !stackedData.categories || !stackedData.series || stackedData.series.length === 0) {
            return this.getColumnChartOption(['No Data'], [0], colors, labelField);
        }

        const series = stackedData.series.map((seriesItem, index) => ({
            name: seriesItem.name,
            type: 'bar',
            stack: 'total',
            data: seriesItem.data,
            barWidth: '60%',
            itemStyle: {
                borderRadius: index === stackedData.series.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]
            },
            emphasis: {
                focus: 'series'
            }
        }));

        return {
            ...this.getAnimationConfig(),
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                },
                formatter: function(params) {
                    let tooltip = `<strong>${params[0].axisValue}</strong><br/>`;
                    let total = 0;
                    params.forEach(param => {
                        const hasUrl = param.data.url && param.data.url !== '#';
                        tooltip += `${param.marker} ${param.seriesName}: ${param.value}${hasUrl ? '<br/><i style="color: #999; font-size: 11px;">Click to view details</i>' : ''}<br/>`;
                        total += param.value;
                    });
                    tooltip += `<strong>Total: ${total}</strong>`;
                    return tooltip;
                }
            },
            legend: {
                ...this.getLegendConfig(),
                show: true,
                type: 'scroll'
            },
            grid: this.getGridConfig(),
            xAxis: {
                type: 'category',
                data: stackedData.categories,
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily,
                    rotate: stackedData.categories.some(cat => cat.length > 8) ? 45 : 0
                },
                axisTick: {
                    show: false
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily
                },
                splitLine: {
                    show: true,
                    lineStyle: {
                        type: 'dashed'
                    }
                }
            },
            color: colors,
            series: series
        };
    },

    // Stacked Horizontal Chart Configuration
    getStackedHorizontalChartOption: function(stackedData, colors, labelField, urls) {
        if (!stackedData || !stackedData.categories || !stackedData.series || stackedData.series.length === 0) {
            return this.getBarChartOption(['No Data'], [0], colors, labelField);
        }

        const series = stackedData.series.map((seriesItem, index) => ({
            name: seriesItem.name,
            type: 'bar',
            stack: 'total',
            data: seriesItem.data,
            barWidth: '60%',
            itemStyle: {
                borderRadius: index === stackedData.series.length - 1 ? [0, 4, 4, 0] : [0, 0, 0, 0]
            },
            emphasis: {
                focus: 'series'
            }
        }));

        return {
            ...this.getAnimationConfig(),
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                },
                formatter: function(params) {
                    let tooltip = `<strong>${params[0].axisValue}</strong><br/>`;
                    let total = 0;
                    params.forEach(param => {
                        const hasUrl = param.data.url && param.data.url !== '#';
                        tooltip += `${param.marker} ${param.seriesName}: ${param.value}${hasUrl ? '<br/><i style="color: #999; font-size: 11px;">Click to view details</i>' : ''}<br/>`;
                        total += param.value;
                    });
                    tooltip += `<strong>Total: ${total}</strong>`;
                    return tooltip;
                }
            },
            legend: {
                ...this.getLegendConfig(),
                show: true,
                type: 'scroll'
            },
            grid: {
                ...this.getGridConfig(),
                left: '5%'
            },
            xAxis: {
                type: 'value',
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily
                },
                splitLine: {
                    show: true,
                    lineStyle: {
                        type: 'dashed'
                    }
                }
            },
            yAxis: {
                type: 'category',
                data: stackedData.categories,
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily
                },
                axisTick: {
                    show: false
                }
            },
            color: colors,
            series: series
        };
    },

    // Area Chart Configuration
    getAreaChartOption: function(labels, data, colors, labelField) {
        return {
            ...this.getAnimationConfig(),
            tooltip: {
                trigger: 'axis'
            },
            legend: this.getLegendConfig(),
            grid: this.getGridConfig(),
            xAxis: {
                type: 'category',
                data: labels,
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    fontSize: this.commonStyles.axisFontSize,
                    fontFamily: this.commonStyles.fontFamily
                }
            },
            color: colors,
            series: [{
                name: labelField,
                type: 'line',
                data: data,
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                lineStyle: {
                    width: 3
                },
                areaStyle: {
                    opacity: 0.3
                }
            }]
        };
    },

    // Animation configurations
    getAnimationConfig: function() {
        return {
            animation: true,
            animationThreshold: 2000,
            animationDuration: 1000,
            animationEasing: 'cubicOut',
            animationDelay: function (idx) {
                return idx * 10;
            },
            animationDurationUpdate: 300,
            animationEasingUpdate: 'cubicOut',
            animationDelayUpdate: function (idx) {
                return idx * 10;
            }
        };
    },

    // Utility function to format numbers
    formatNumber: function(num, decimals = 0) {
        if (num === null || num === undefined) return '0';

        const factor = Math.pow(10, decimals);
        const formatted = Math.round(num * factor) / factor;

        return formatted.toLocaleString();
    },

    // Utility function to get dynamic colors based on data length
    getDynamicColors: function(dataLength) {
        const colors = [...this.defaultColors];

        while (colors.length < dataLength) {
            // Generate additional colors if needed
            const hue = (colors.length * 137.5) % 360; // Golden angle for color distribution
            colors.push(`hsl(${hue}, 70%, 60%)`);
        }

        return colors.slice(0, dataLength);
    },

    attachClickHandler: function(chartInstance, urls) {
        if (!urls || urls.length === 0) return;

        chartInstance.on('click', function(params) {
            let targetUrl = null;

            if (params.data && params.data.url) {
                targetUrl = params.data.url;
            }
            else if (params.seriesIndex !== undefined && params.seriesIndex < urls.length) {
                targetUrl = urls[params.seriesIndex];
            }
            else if (params.dataIndex !== undefined && params.dataIndex < urls.length) {
                targetUrl = urls[params.dataIndex];
            }

            if (targetUrl && targetUrl !== '#') {
                if (typeof htmx !== 'undefined') {
                    const tempLink = document.createElement('a');
                    tempLink.href = targetUrl;
                    tempLink.setAttribute('hx-get', targetUrl);
                    tempLink.setAttribute('hx-target', '#mainContent');
                    tempLink.setAttribute('hx-swap', 'outerHTML');
                    tempLink.setAttribute('hx-push-url', 'true');
                    tempLink.setAttribute('hx-select', '#mainContent');
                    tempLink.setAttribute('hx-select-oob', '#sideMenuContainer');

                    htmx.process(tempLink);

                    tempLink.click();
                } else {
                    window.location.href = targetUrl;
                }
            }
        });

        chartInstance.on('mouseover', function(params) {
            let hasUrl = false;

            if (params.data && params.data.url && params.data.url !== '#') {
                hasUrl = true;
            } else if (urls && (params.dataIndex < urls.length || params.seriesIndex < urls.length)) {
                hasUrl = true;
            }

            if (hasUrl) {
                chartInstance.getDom().style.cursor = 'pointer';
            }
        });

        chartInstance.on('mouseout', function() {
            chartInstance.getDom().style.cursor = 'default';
        });
    },

    // Export chart as image (requires additional setup)
    exportChart: function(chartInstance, filename = 'chart', format = 'png') {
        if (!chartInstance) return;

        const url = chartInstance.getDataURL({
            pixelRatio: 2,
            backgroundColor: '#fff',
            excludeComponents: ['toolbox']
        });

        const link = document.createElement('a');
        link.download = `${filename}.${format}`;
        link.href = url;
        link.click();
    }
};

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EChartsConfig;
}
