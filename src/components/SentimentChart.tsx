"use client"

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

type SentimentData = {
  date: string
  market_index: number
  super_short_sentiment: number
  losing_money_effect: number
  details?: {
    up_count: number | null
    limit_up_count: number
    bomb_count: number
    limit_down_count: number
    sse_change_pct?: number
  }
}

interface SentimentChartProps {
  data: SentimentData[]
}

export function SentimentChart({ data }: SentimentChartProps) {
  return (
    <div className="flex flex-col gap-6">
      <Card className="w-full h-full min-h-[500px]">
        <CardHeader>
          <CardTitle>市场情绪周期指标</CardTitle>
          <CardDescription>
            基于量化分析的市场情绪追踪。每日收盘后更新。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted/30" />
                <XAxis
                  dataKey="date"
                  stroke="#888888"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => value.slice(4)} // Show MMDD
                />
                <YAxis
                  stroke="#888888"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => `${value}`}
                />
                <Tooltip
                  labelFormatter={(label) => `日期: ${label}`}
                  formatter={(value, name) => {
                    const nameMap: Record<string, string> = {
                      market_index: "大盘指数 (红)",
                      super_short_sentiment: "超短情绪 (紫)",
                      losing_money_effect: "亏钱效应 (绿)",
                    };
                    const key = String(name);
                    return [value ?? "-", nameMap[key] || key];
                  }}
                />
                <Legend
                  verticalAlign="top"
                  height={36}
                  formatter={(value) => {
                    const nameMap: Record<string, string> = {
                      market_index: "大盘指数 (红)",
                      super_short_sentiment: "超短情绪 (紫)",
                      losing_money_effect: "亏钱效应 (绿)",
                    };
                    return <span className="font-bold mx-2">{nameMap[value]}</span>;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="market_index"
                  name="market_index"
                  stroke="#ef4444"
                  strokeWidth={3}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  label={(props) => {
                    const { x, y, value, index } = props;
                    if (index === undefined) return null;
                    const item = data[index];
                    if (item && (item.losing_money_effect > item.market_index || item.losing_money_effect > item.super_short_sentiment)) {
                      return <text x={x} y={y} dy={-10} fill="#ef4444" fontSize={11} textAnchor="middle" fontWeight="bold">{value}</text>;
                    }
                    return null;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="super_short_sentiment"
                  name="super_short_sentiment"
                  stroke="#a855f7"
                  strokeWidth={3}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  label={(props) => {
                    const { x, y, value, index } = props;
                    if (index === undefined) return null;
                    const item = data[index];
                    if (item && (item.losing_money_effect > item.market_index || item.losing_money_effect > item.super_short_sentiment)) {
                      return <text x={x} y={y} dy={-10} fill="#a855f7" fontSize={11} textAnchor="middle" fontWeight="bold">{value}</text>;
                    }
                    return null;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="losing_money_effect"
                  name="losing_money_effect"
                  stroke="#22c55e"
                  strokeWidth={3}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  label={(props) => {
                    const { x, y, value, index } = props;
                    if (index === undefined) return null;
                    const item = data[index];
                    if (item && (item.losing_money_effect > item.market_index || item.losing_money_effect > item.super_short_sentiment)) {
                      return <text x={x} y={y} dy={-10} fill="#22c55e" fontSize={11} textAnchor="middle" fontWeight="bold">{value}</text>;
                    }
                    return null;
                  }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>指标计算公式</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <h4 className="font-semibold text-red-500">大盘指数 (Market Index)</h4>
              <p className="text-muted-foreground">
                用于判断市场整体环境冷暖。
                <br />
                <code>公式 = 全市场上涨家数 / 20</code>
                <br />
                <span className="text-xs text-gray-500">* 历史数据部分使用「上证指数涨跌幅」进行估算回溯。</span>
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-purple-600">超短情绪 (Super Short Sentiment)</h4>
              <p className="text-muted-foreground">
                用于判断短线资金的活跃程度。
                <br />
                <code>公式 = 涨停家数 + (创月新高家数 / 2) + 昨日涨停溢价</code>
                <br />
                <span className="text-xs text-gray-500">* 历史数据主要基于「涨停家数」。</span>
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-green-600">亏钱效应 (Losing Money Effect)</h4>
              <p className="text-muted-foreground">
                用于判断市场恐慌程度，是抄底的重要信号（冰点）。
                <br />
                <code>公式 = (炸板率 * 100) + (跌停家数 + 大跌家数) * 2</code>
                <br />
                <span className="text-xs text-gray-500">* 历史数据主要基于「跌停家数」与「炸板率」。</span>
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>每日详细数据 (最近10日)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-center">
                <thead className="text-xs uppercase bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                  <tr>
                    <th className="px-3 py-2 text-left">日期 (Date)</th>
                    {/* Raw Data Group */}
                    <th className="px-1 py-2 bg-blue-50/50 dark:bg-blue-900/10 text-blue-600">涨停(原始)</th>
                    <th className="px-1 py-2 bg-blue-50/50 dark:bg-blue-900/10 text-blue-600">跌停(原始)</th>
                    <th className="px-1 py-2 bg-blue-50/50 dark:bg-blue-900/10 text-blue-600">炸板(原始)</th>
                    <th className="px-1 py-2 bg-blue-50/50 dark:bg-blue-900/10 text-blue-600">上涨数/涨幅</th>
                    {/* Calculated Indicators Group */}
                    <th className="px-1 py-2 text-red-600 border-l border-gray-200 dark:border-gray-700">大盘(计算)</th>
                    <th className="px-1 py-2 text-purple-600">情绪(计算)</th>
                    <th className="px-1 py-2 text-green-600">亏钱(计算)</th>
                  </tr>
                </thead>
                <tbody>
                  {[...data].reverse().slice(0, 10).map((item) => (
                    <tr key={item.date} className="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-3 py-2 font-medium text-left font-mono">{item.date}</td>

                      {/* Raw Data */}
                      <td className="px-1 py-2 bg-blue-50/30 dark:bg-blue-900/5 text-red-500 font-medium">
                        {item.details?.limit_up_count ?? '-'}
                      </td>
                      <td className="px-1 py-2 bg-blue-50/30 dark:bg-blue-900/5 text-green-500 font-medium">
                        {item.details?.limit_down_count ?? '-'}
                      </td>
                      <td className="px-1 py-2 bg-blue-50/30 dark:bg-blue-900/5 text-gray-500 font-medium">
                        {item.details?.bomb_count ?? '-'}
                      </td>
                      <td className="px-1 py-2 bg-blue-50/30 dark:bg-blue-900/5 text-xs">
                        {item.details?.up_count != null ? (
                          <span className="text-red-600">{item.details.up_count} 家</span>
                        ) : item.details?.sse_change_pct != null ? (
                          <span className="text-gray-500 font-mono text-[10px]">
                            {item.details.sse_change_pct > 0 ? '+' : ''}{item.details.sse_change_pct}%
                          </span>
                        ) : (
                          '-'
                        )}
                      </td>

                      {/* Calculated Indicators */}
                      <td className="px-1 py-2 border-l border-gray-200 dark:border-gray-700 text-red-600 font-bold">
                        {item.market_index}
                      </td>
                      <td className="px-1 py-2 text-purple-600 font-bold">
                        {item.super_short_sentiment}
                      </td>
                      <td className="px-1 py-2 text-green-600 font-bold">
                        {item.losing_money_effect}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8">
        <details className="group">
          <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground list-none flex items-center gap-2 select-none">
            <span className="transition-transform group-open:rotate-90">▶</span>
            查看原始 JSON 数据 (Debugging)
          </summary>
          <div className="mt-4 p-4 bg-gray-100 dark:bg-gray-900 rounded-lg overflow-x-auto max-h-[500px]">
            <pre className="text-xs font-mono text-muted-foreground">
              {JSON.stringify(
                data
                  .map(({ date, details }) => ({
                    date,
                    ...(details || {}),
                  }))
                  .reverse(),
                null,
                2
              )}
            </pre>
          </div>
        </details>
      </div>
    </div>
  )
}
