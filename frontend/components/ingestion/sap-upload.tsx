'use client';

import { useState } from 'react';
import { postForm } from '@/lib/api';
import { IngestionResponse, RawEmission } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, CheckCircle2, Loader2, Upload } from 'lucide-react';

export default function SAPUpload() {
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

    const response = await postForm<IngestionResponse>('/ingestion/sap/', formData);

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
      {/* Upload Area */}
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
              SAP fuel and procurement CSV export
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

      {/* Error */}
      {error && (
        <div className="flex gap-2 bg-destructive/10 border border-destructive/30 rounded-md p-3">
          <AlertCircle className="h-5 w-5 text-destructive flex-shrink-0" />
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {/* Upload Button */}
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

      {/* Results */}
      {result && (
        <div className="space-y-4">
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
              {result.errors.length > 0 && (
                <CardDescription className="text-amber-900">
                  {result.errors.length} error{result.errors.length !== 1 ? 's' : ''}
                </CardDescription>
              )}
            </CardHeader>
          </Card>

          {/* Errors */}
          {result.errors.length > 0 && (
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="text-base">Errors</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.errors.map((error, idx) => (
                    <li key={idx} className="text-sm text-red-700 flex gap-2">
                      <span>•</span>
                      {error}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Warnings */}
          {result.warnings.length > 0 && (
            <Card className="border-amber-200">
              <CardHeader>
                <CardTitle className="text-base">Warnings</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.warnings.map((warning, idx) => (
                    <li key={idx} className="text-sm text-amber-700 flex gap-2">
                      <span>•</span>
                      {warning}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Sample Records */}
          {result.created_records.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Sample Records</CardTitle>
                <CardDescription>
                  Showing first 3 of {result.created_records.length} created
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {result.created_records.slice(0, 3).map((record) => (
                    <div key={record.id} className="p-3 border rounded-md text-sm">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-medium">{record.activity_type}</p>
                          <p className="text-xs text-muted-foreground">
                            {record.activity_value} {record.activity_unit} → {parseFloat(String(record.calculated_emissions_kg_co2e)).toFixed(2)} kg CO₂e
                          </p>
                        </div>
                        {record.validation_issues?.length > 0 && (
                          <Badge variant="outline" className="bg-amber-50 text-amber-900">
                            {record.validation_issues.length} issue{record.validation_issues.length !== 1 ? 's' : ''}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Help */}
      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-sm">Expected CSV Format</CardTitle>
        </CardHeader>
        <CardContent className="text-xs space-y-1">
          <p>Columns: PO#, Material Code, Plant Code, Date, Quantity, Unit of Measure, Cost, Vendor</p>
          <p className="text-muted-foreground">
            Example: 12345, FUEL-DIESEL, PLANT-A, 2024-01-15, 500, L, 1000, VendorName
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
