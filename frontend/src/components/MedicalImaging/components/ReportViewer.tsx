import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Download, 
  Share2, 
  Printer, 
  FileText, 
  CheckCircle, 
  AlertTriangle, 
  Info,
  TrendingUp,
  TrendingDown,
  Activity
} from 'lucide-react';

interface Finding {
  id: string;
  type: 'normal' | 'abnormal' | 'critical';
  title: string;
  description: string;
  confidence: number;
  location?: string;
  recommendations?: string[];
}

interface Statistic {
  label: string;
  value: number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  changePercent?: number;
}

interface ReportViewerProps {
  patientName: string;
  patientId: string;
  studyDate: Date;
  studyType: string;
  findings: Finding[];
  statistics?: Statistic[];
  conclusion?: string;
  recommendations?: string[];
  images?: { url: string; caption: string }[];
  onExport?: (format: 'pdf' | 'json' | 'print') => void;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({
  patientName,
  patientId,
  studyDate,
  studyType,
  findings,
  statistics = [],
  conclusion,
  recommendations = [],
  images = [],
  onExport
}) => {
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [activeTab, setActiveTab] = useState<'findings' | 'stats' | 'images'>('findings');
  const reportRef = useRef<HTMLDivElement>(null);

  // Get icon for finding type
  const getFindingIcon = (type: Finding['type']) => {
    switch (type) {
      case 'critical':
        return <AlertTriangle className="w-5 h-5 text-red-500" />;
      case 'abnormal':
        return <Info className="w-5 h-5 text-yellow-500" />;
      case 'normal':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
    }
  };

  // Get trend icon
  const getTrendIcon = (trend?: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-green-500" />;
      case 'down':
        return <TrendingDown className="w-4 h-4 text-red-500" />;
      default:
        return <Activity className="w-4 h-4 text-gray-400" />;
    }
  };

  // Handle export
  const handleExport = (format: 'pdf' | 'json' | 'print') => {
    if (onExport) {
      onExport(format);
    } else {
      // Default export behavior
      switch (format) {
        case 'print':
          window.print();
          break;
        case 'json':
          const data = {
            patientName,
            patientId,
            studyDate,
            studyType,
            findings,
            statistics,
            conclusion,
            recommendations
          };
          const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `report_${patientId}_${new Date().getTime()}.json`;
          a.click();
          URL.revokeObjectURL(url);
          break;
        case 'pdf':
          // Would require a PDF generation library
          alert('PDF export requires additional setup');
          break;
      }
    }
  };

  // Count findings by type
  const findingCounts = findings.reduce((acc, finding) => {
    acc[finding.type] = (acc[finding.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <motion.div
      ref={reportRef}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-900 rounded-xl shadow-2xl overflow-hidden"
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">Medical Imaging Report</h1>
            <div className="grid grid-cols-2 gap-4 text-sm text-blue-100">
              <div>
                <span className="opacity-75">Patient:</span> {patientName} (ID: {patientId})
              </div>
              <div>
                <span className="opacity-75">Study Type:</span> {studyType}
              </div>
              <div>
                <span className="opacity-75">Study Date:</span> {studyDate.toLocaleDateString()}
              </div>
              <div>
                <span className="opacity-75">Report Date:</span> {new Date().toLocaleDateString()}
              </div>
            </div>
          </div>
          
          {/* Export Options */}
          <div className="flex space-x-2">
            <button
              onClick={() => handleExport('pdf')}
              className="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
              title="Export as PDF"
            >
              <Download className="w-5 h-5 text-white" />
            </button>
            <button
              onClick={() => handleExport('print')}
              className="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
              title="Print"
            >
              <Printer className="w-5 h-5 text-white" />
            </button>
            <button
              onClick={() => handleExport('json')}
              className="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
              title="Export as JSON"
            >
              <FileText className="w-5 h-5 text-white" />
            </button>
            <button
              className="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors"
              title="Share"
            >
              <Share2 className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4 mt-6">
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="bg-white/20 backdrop-blur-sm rounded-lg p-3 text-center"
          >
            <div className="flex items-center justify-center mb-1">
              <CheckCircle className="w-5 h-5 text-green-300 mr-2" />
              <span className="text-2xl font-bold text-white">{findingCounts.normal || 0}</span>
            </div>
            <p className="text-sm text-blue-100">Normal</p>
          </motion.div>
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="bg-white/20 backdrop-blur-sm rounded-lg p-3 text-center"
          >
            <div className="flex items-center justify-center mb-1">
              <Info className="w-5 h-5 text-yellow-300 mr-2" />
              <span className="text-2xl font-bold text-white">{findingCounts.abnormal || 0}</span>
            </div>
            <p className="text-sm text-blue-100">Abnormal</p>
          </motion.div>
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="bg-white/20 backdrop-blur-sm rounded-lg p-3 text-center"
          >
            <div className="flex items-center justify-center mb-1">
              <AlertTriangle className="w-5 h-5 text-red-300 mr-2" />
              <span className="text-2xl font-bold text-white">{findingCounts.critical || 0}</span>
            </div>
            <p className="text-sm text-blue-100">Critical</p>
          </motion.div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800">
        {['findings', 'stats', 'images'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab as any)}
            className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'text-blue-500 border-b-2 border-blue-500 bg-gray-800/50'
                : 'text-gray-400 hover:text-gray-300'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-6">
        <AnimatePresence mode="wait">
          {/* Findings Tab */}
          {activeTab === 'findings' && (
            <motion.div
              key="findings"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
            >
              {findings.map((finding, index) => (
                <motion.div
                  key={finding.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`bg-gray-800 rounded-lg p-4 cursor-pointer transition-all ${
                    selectedFinding?.id === finding.id ? 'ring-2 ring-blue-500' : ''
                  }`}
                  onClick={() => setSelectedFinding(finding)}
                  whileHover={{ scale: 1.01 }}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center">
                      {getFindingIcon(finding.type)}
                      <h3 className="ml-3 font-medium text-gray-200">{finding.title}</h3>
                    </div>
                    <div className="flex items-center space-x-2">
                      {finding.location && (
                        <span className="text-xs text-gray-500 bg-gray-700 px-2 py-1 rounded">
                          {finding.location}
                        </span>
                      )}
                      <span className="text-xs text-gray-400">
                        {Math.round(finding.confidence * 100)}% confidence
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-400 mb-2">{finding.description}</p>
                  
                  {/* Progress bar for confidence */}
                  <div className="w-full bg-gray-700 rounded-full h-1 mt-3">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${finding.confidence * 100}%` }}
                      className={`h-1 rounded-full ${
                        finding.type === 'critical' ? 'bg-red-500' :
                        finding.type === 'abnormal' ? 'bg-yellow-500' :
                        'bg-green-500'
                      }`}
                    />
                  </div>

                  {/* Recommendations */}
                  {finding.recommendations && finding.recommendations.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-700">
                      <p className="text-xs text-gray-500 mb-1">Recommendations:</p>
                      <ul className="text-xs text-gray-400 space-y-1">
                        {finding.recommendations.map((rec, idx) => (
                          <li key={idx} className="flex items-start">
                            <span className="mr-2">•</span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </motion.div>
              ))}
            </motion.div>
          )}

          {/* Statistics Tab */}
          {activeTab === 'stats' && (
            <motion.div
              key="stats"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="grid grid-cols-2 md:grid-cols-3 gap-4"
            >
              {statistics.map((stat, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-gray-800 rounded-lg p-4"
                  whileHover={{ scale: 1.05 }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm text-gray-400">{stat.label}</p>
                    {getTrendIcon(stat.trend)}
                  </div>
                  <div className="flex items-baseline">
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="text-2xl font-bold text-gray-200"
                    >
                      {stat.value}
                    </motion.span>
                    {stat.unit && (
                      <span className="ml-1 text-sm text-gray-500">{stat.unit}</span>
                    )}
                  </div>
                  {stat.changePercent !== undefined && (
                    <p className={`text-xs mt-1 ${
                      stat.changePercent > 0 ? 'text-green-400' : 
                      stat.changePercent < 0 ? 'text-red-400' : 
                      'text-gray-400'
                    }`}>
                      {stat.changePercent > 0 ? '+' : ''}{stat.changePercent}% from previous
                    </p>
                  )}
                </motion.div>
              ))}
            </motion.div>
          )}

          {/* Images Tab */}
          {activeTab === 'images' && (
            <motion.div
              key="images"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="grid grid-cols-2 md:grid-cols-3 gap-4"
            >
              {images.map((image, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-gray-800 rounded-lg overflow-hidden"
                  whileHover={{ scale: 1.05 }}
                >
                  <img
                    src={image.url}
                    alt={image.caption}
                    className="w-full h-48 object-cover"
                  />
                  <p className="p-3 text-sm text-gray-400">{image.caption}</p>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Conclusion Section */}
      {conclusion && (
        <div className="p-6 border-t border-gray-800">
          <h3 className="text-lg font-semibold text-gray-200 mb-3">Conclusion</h3>
          <p className="text-gray-400">{conclusion}</p>
        </div>
      )}

      {/* Overall Recommendations */}
      {recommendations.length > 0 && (
        <div className="p-6 border-t border-gray-800">
          <h3 className="text-lg font-semibold text-gray-200 mb-3">Recommendations</h3>
          <ul className="space-y-2">
            {recommendations.map((rec, index) => (
              <motion.li
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-start text-gray-400"
              >
                <CheckCircle className="w-4 h-4 text-blue-500 mr-2 mt-0.5 flex-shrink-0" />
                <span className="text-sm">{rec}</span>
              </motion.li>
            ))}
          </ul>
        </div>
      )}
    </motion.div>
  );
};

export default ReportViewer;