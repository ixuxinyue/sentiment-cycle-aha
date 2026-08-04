import { promises as fs } from 'fs';
import path from 'path';
import { SentimentChart } from '@/components/SentimentChart';

async function getData() {
  try {
    const filePath = path.join(process.cwd(), 'public', 'data.json');
    const fileContents = await fs.readFile(filePath, 'utf8');
    return JSON.parse(fileContents);
  } catch (error) {
    console.warn("Could not read data.json, returning empty array.", error);
    return [];
  }
}

export default async function Home() {
  const data = await getData();
  const latestDate = data.at(-1)?.date;

  return (
    <div className="container mx-auto py-10 px-4">
      <div className="flex flex-col gap-8">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">市场情绪周期 (Market Sentiment Cycle)</h1>
          <p className="text-muted-foreground">
            基于量化分析的市场情绪追踪系统。每日收盘后自动更新。
          </p>
          <p className="text-sm text-muted-foreground">当前数据: {latestDate ?? "暂无数据"}</p>
        </div>

        <SentimentChart data={data} />

        {/* Overview Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          {data.length > 0 && (
            <>
              <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
                <div className="text-sm font-medium text-red-500">最新大盘指数</div>
                <div className="text-2xl font-bold">{data[data.length - 1].market_index}</div>
                <div className="text-xs text-muted-foreground mt-1">反映市场整体赚钱效应</div>
              </div>
              <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
                <div className="text-sm font-medium text-purple-600">最新超短情绪</div>
                <div className="text-2xl font-bold">{data[data.length - 1].super_short_sentiment}</div>
                <div className="text-xs text-muted-foreground mt-1">反映龙头与连板活跃度</div>
              </div>
              <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
                <div className="text-sm font-medium text-green-600">最新亏钱效应</div>
                <div className="text-2xl font-bold">{data[data.length - 1].losing_money_effect}</div>
                <div className="text-xs text-muted-foreground mt-1">反映跌停与核按钮恐慌度</div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
