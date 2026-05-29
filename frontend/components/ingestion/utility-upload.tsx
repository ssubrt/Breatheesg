'use client';

import { useState } from 'react';
import { postForm } from '@/lib/api';
import { IngestionResponse } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, CheckCircle2, Loader2, Upload } from 'lucide-react';

export default function UtilityUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IngestionResponse | null>(null);
  const [error, setError] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0]);
      setError('');
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    const response = await postForm<IngestionResponse>('/ingestion/utility/', formData);

    if ('error' in response || 'detail' in response) {
      setError(response.error || response.detail || 'Upload failed');
    } else {
      setResult(response);
      setFile(null);
    }

    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-8">
        <div className="space-y-4">
          <label
            htmlFor="file-upload"
            className="flex flex-col items-center gap-2 cursor-pointer"
          >
            <Upload className="h-8 w-8 text-muted-foreground" />
            <span className="text-sm font-medium">
              Click to select a CSV file
            </span>
            <span className="text-xs text-muted-foreground">
              Utility meter readings CSV export
            </span>
          </label>
          <input
            id="file-upload"
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            disabled={loading}
            className="hidden"
          />
        </div>

        {file && (
          <div className="mt-4 p-3 bg-muted rounded-md">
            <p className="text-sm">Selected: <span className="font-medium">{file.name}</span></p>
          </div>
        )}
      </div>

      {error && (
        <div className="flex gap-2 bg-destructive/10 border border-destructive/30 rounded-md p-3">
          <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0" />
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      <Button
        onClick={handleUpload}
        disabled={!file || loading}
        className="w-full"
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Uploading...
          </>
        ) : (
          'Upload CSV'
        )}
      </Button>

      {result && (
        <Card className={result.errors.length === 0 ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'}>
          <CardHeader>
            <div className="flex items-center gap-2">
              {result.errors.length === 0 ? (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              ) : (
                <AlertCircle className="h-5 w-5 text-amber-600" />
              )}
              <CardTitle className="text-base">
                {result.ingested_count} records ingested
              </CardTitle>
            </div>
          </CardHeader>
        </Card>
      )}

      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-sm">Expected CSV Format</CardTitle>
        </CardHeader>
        <CardContent className="text-xs space-y-1">
          <p>Columns: Meter ID, Reading Date, kWh, Tariff Code</p>
          <p className="text-muted-foreground">
            Example: METER001, 2024-01-15, 1250.5, GRID_AVG
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
