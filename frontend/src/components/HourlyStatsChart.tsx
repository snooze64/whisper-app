/**
 * Hourly statistics chart component using Chart.js
 */
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import { HourlyStats } from '@/types/admin'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface HourlyStatsChartProps {
  hourlyStats: HourlyStats[]
}

export default function HourlyStatsChart({ hourlyStats }: HourlyStatsChartProps) {
  // Format the data for Chart.js
  const labels = hourlyStats.map((stat) => {
    const date = new Date(stat.hour)
    return date.toLocaleString('ja-JP', { month: 'short', day: 'numeric', hour: '2-digit' })
  })

  const data = {
    labels,
    datasets: [
      {
        label: '成功',
        data: hourlyStats.map((stat) => stat.successful),
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: true,
        tension: 0.4,
      },
      {
        label: '失敗',
        data: hourlyStats.map((stat) => stat.failed),
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: false,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
      },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
      },
      y: {
        beginAtZero: true,
        ticks: {
          precision: 0,
        },
      },
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false,
    },
  }

  return (
    <div style={{ height: '300px' }}>
      <Line data={data} options={options} />
    </div>
  )
}
