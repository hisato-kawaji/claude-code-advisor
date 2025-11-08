import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { statsApi } from '../api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import './MonitoringPage.css';

// Helper to get yesterday's date in YYYY-MM-DD format
const getYesterday = () => {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return yesterday.toISOString().split('T')[0];
};

export function MonitoringPage() {
  const [selectedDate, setSelectedDate] = useState<string>(getYesterday());

  const { data: hourlyData, isLoading, isError, error } = useQuery({
    queryKey: ['hourlyStats', selectedDate],
    queryFn: () => statsApi.getHourly(selectedDate).then(res => res.data),
    enabled: !!selectedDate, // Only run query if a date is selected
  });

  // Calculate cumulative data for the table
  const tableData = useMemo(() => {
    if (!hourlyData) return [];
    let cumulativeInput = 0;
    let cumulativeOutput = 0;
    return hourlyData.map(d => {
      cumulativeInput += d.input_tokens;
      cumulativeOutput += d.output_tokens;
      return {
        ...d,
        cumulative_input: cumulativeInput,
        cumulative_output: cumulativeOutput,
      };
    });
  }, [hourlyData]);

  return (
    <div className="monitoring-page">
      <div className="page-header">
        <h1>🕒 1時間ごとのトークン消費量</h1>
        <div className="date-picker-container">
          <label htmlFor="date-select">日付を選択:</label>
          <input
            type="date"
            id="date-select"
            value={selectedDate}
            max={getYesterday()} // Don't allow selecting today or future dates
            onChange={(e) => setSelectedDate(e.target.value)}
          />
        </div>
      </div>

      <div className="chart-container">
        {isLoading && <p>グラフを読み込み中...</p>}
        {isError && <p className="error-message">エラーが発生しました: {error.message}</p>}
        {hourlyData && (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart
              data={hourlyData}
              margin={{
                top: 5,
                right: 30,
                left: 20,
                bottom: 5,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" label={{ value: '時間 (時)', position: 'insideBottom', offset: -5 }} />
              <YAxis label={{ value: 'トークン数', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend verticalAlign="top" />
              <Bar dataKey="input_tokens" name="Input Tokens" fill="#8884d8" />
              <Bar dataKey="output_tokens" name="Output Tokens" fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {tableData && tableData.length > 0 && (
        <div className="table-container">
          <h3>時間別データ</h3>
          <table>
            <thead>
              <tr>
                <th>時間</th>
                <th>Input Tokens</th>
                <th>Output Tokens</th>
                <th>累積 Input</th>
                <th>累積 Output</th>
              </tr>
            </thead>
            <tbody>
              {tableData.map((row) => (
                <tr key={row.hour}>
                  <td>{`${row.hour}:00 - ${row.hour}:59`}</td>
                  <td>{row.input_tokens.toLocaleString()}</td>
                  <td>{row.output_tokens.toLocaleString()}</td>
                  <td>{row.cumulative_input.toLocaleString()}</td>
                  <td>{row.cumulative_output.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}