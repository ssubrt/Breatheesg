'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import SAPUpload from '@/components/ingestion/sap-upload';
import UtilityUpload from '@/components/ingestion/utility-upload';
import TravelUpload from '@/components/ingestion/travel-upload';

export default function IngestPage() {
  const [activeTab, setActiveTab] = useState('sap');

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Ingest Data</h1>
        <p className="text-muted-foreground mt-1">
          Upload emissions data from different sources
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Data Sources</CardTitle>
          <CardDescription>
            Select a source and upload or paste data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="sap">SAP Procurement</TabsTrigger>
              <TabsTrigger value="utility">Utility Meters</TabsTrigger>
              <TabsTrigger value="travel">Travel Expenses</TabsTrigger>
            </TabsList>

            <TabsContent value="sap" className="mt-6">
              <SAPUpload />
            </TabsContent>

            <TabsContent value="utility" className="mt-6">
              <UtilityUpload />
            </TabsContent>

            <TabsContent value="travel" className="mt-6">
              <TravelUpload />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
