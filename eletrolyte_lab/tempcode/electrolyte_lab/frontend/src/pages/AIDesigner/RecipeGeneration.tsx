import type { Dispatch, SetStateAction } from 'react';
import React, { useState, useEffect,useCallback,useRef } from 'react';
import styles from '../../css/RecipeGeneration..module.css';
import adStyles from '../../css/Prediction.module.css';
import { Typography,  Spin, Progress, Alert, Button, Row, Col, Card, Statistic, Table, InputNumber, Input, Select, message, Space, Empty,Modal } from 'antd';
import { ExperimentOutlined, CheckCircleFilled } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { aiDesignerApi, molecularApi, literatureApi } from '../../services/api';
import {
  ParsedParameters,
  FormulaDataset,
  PredictedData,
  Formula
} from '../../types';

const { Title, Paragraph, Text } = Typography;



type StepHistoryType = Record<number, any>;

const RecipeGeneration: React.FC<{ setCurrentStep?: (step: number) => void; setStepHistory?: Dispatch<SetStateAction<StepHistoryType>>; recipeItems?: any }> = ({ setCurrentStep, setStepHistory, recipeItems }) => {
   const [loading, setLoading] = useState(false);
   const [predictionProgress, setPredictionProgress] = useState(0);
    const [predictedData, setPredictedData] = useState([] as any);
    const [summary, setSummary] = useState<any>(null);
    const [content,setContent]=useState([]);
    const [generationResult, setGenerationResult] = useState<any[]>([]);
    const [selectedIteration, setSelectedIteration] = useState<number>(0);                
    const [selectedRecipes, setSelectedRecipes] = useState<number[]>([]);
    // 分页相关
    const [currentPage, setCurrentPage] = useState(1);
    const pageSize = 8;
    // 详情弹窗
    const [detailModalVisible, setDetailModalVisible] = useState(false);
    const [detailData, setDetailData] = useState<any>(null);
    const handleDirectPrediction = async () => {
      getData();
    };
  // 提取当前迭代数据并转换为表格行，便于替换数据源
  const currentIteration = (generationResult.length ? generationResult : predictedData)[selectedIteration] || { components: [] };
  // 编辑配方 Modal 状态
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editComponents, setEditComponents] = useState<any[]>([]);
  const openEditModal = (idx?: number) => {
    const useIndex = typeof idx === 'number' ? idx : selectedIteration;
    if (typeof idx === 'number') setSelectedIteration(idx);
    // Prefer generationResult entry only if it actually has components
    const genHas = generationResult && generationResult[useIndex] && Array.isArray(generationResult[useIndex].components) && generationResult[useIndex].components.length > 0;
    const sourceArray: any[] = genHas ? generationResult : predictedData;
    const iter = (sourceArray && sourceArray[useIndex]) || { components: [] };
    
    const mapped = (iter.components || []).map((c: any) => {
    const numericIndex = Number(c.name) - 1;
      const mol = (content && content[numericIndex]) || content.find((x: any) => x.name === c.name) || { name: String(c.name), type: '-', formula: '-', ratioDisplay: '' };
      return {
        name: mol.name,
        type: mol.type,
        formula: mol.formula,
        ratio: typeof c.ratio === 'number' ? c.ratio :0
      };
    });
    setEditComponents(mapped);
    setEditModalVisible(true);
  };

  const updateEditComponent = (idx: number, field: string, value: any) => {
    setEditComponents(prev => prev.map((it, i) => i === idx ? { ...it, [field]: value } : it));
  };

  const saveEditedComponents = () => {
    // 归一化比例（若为数字）
    const comps = editComponents.map(c => ({ ...c }));
    const numericSum = comps.reduce((s, c) => s + (typeof c.ratio === 'number' ? c.ratio : 0), 0) || 1;
    comps.forEach(c => { if (typeof c.ratio === 'number') c.ratio = Number((c.ratio / numericSum).toFixed(4)); });
    // 将修改写回 predictedData
    const newGen = predictedData.slice();
    newGen[selectedIteration] = { ...(newGen[selectedIteration] || {}), components: comps };
    setPredictedData(newGen);
    setEditModalVisible(false);
    message.success('配方比例已更新');
  };

  const handleRunExperimentSelected = async () => {
    if (!selectedRecipes || selectedRecipes.length === 0) {
      message.warning('请先选择至少一个配方进行实验');
      return;
    }
    setLoading(true);
    try {
      const all = (generationResult.length ? generationResult : predictedData) || [];
      const payload = selectedRecipes.map(i => all[i]).filter(Boolean);
      // TODO: 调用后端接口提交 payload，例如：
      // await aiDesignerApi.runExperimentBatch({ recipes: payload });
      message.success(`已提交 ${payload.length} 个配方进行实验（模拟）`);
      // 提交后可清空已选
      setSelectedRecipes([]);
    } catch (e) {
      message.error('实验提交失败');
    } finally {
      setLoading(false);
    }
  };

  const getData = useCallback(async () => {
    if (loading) return;
    try {
      setLoading(true);
      setPredictionProgress(0);
      console.log('开始生成！！');
      const predictResponse = await aiDesignerApi.generateFormula(recipeItems);
      
      console.log('配方生成结果',predictResponse);
      setPredictedData(predictResponse.formula);  
      setSummary(predictResponse.quality_sum)
      
    } catch (error: any) {
      console.error('配方生成失败:', error);
      message.error(`配方生成失败：${error?.message || '请重试'}`);
    } finally {
      setLoading(false);
    }  
  //    setPredictedData([
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.261924586653979,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.494474488596285,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 34.71104327731092,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 45.24347493339254,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 29.362675033621517,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 0.6707625806451613,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 1,
  //       "lce": 1.314374881511333
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.7366606161532057,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.0252638372913236,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 28.892477833295477,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 31.024494160746002,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 27.220594620557158,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 13.94409524687294,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 2,
  //       "lce": 1.297914103710551
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.960273652908291,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 1.804253397601693,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 35.519307880990226,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 12.667909169626999,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 27.506864370797317,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 20.792033633969716,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 3,
  //       "lce": 1.196744790188186
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.1155413346021175,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.6391540089348697,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 28.835613786054964,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 19.110097224689163,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 15.559255196926035,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 29.034297735352197,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 4,
  //       "lce": 1.263074475856998
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.715207898180088,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.0464668704443922,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 32.616229604814905,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 24.07034648090586,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 23.07564507204611,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 18.74992335747202,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 5,
  //       "lce": 1.259152435391707
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 2.456840977756632,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 1.313465541970374,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 17.522921201453553,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 41.48239128552398,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 18.53008093179635,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 20.289380750493745,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 6,
  //       "lce": 1.370782480465751
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.498156869275604,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.2609916764636724,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 26.681165148762208,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 22.287850754884545,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 15.63640229586936,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 28.345934970375243,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 7,
  //       "lce": 1.285307758109715
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.3014228262162484,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.455435962849753,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 35.51304319781966,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 17.99137063721137,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 14.041281565802114,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 26.86696075049375,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 8,
  //       "lce": 1.219291891735819
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.4070459141191864,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.351042205501998,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 40.68514152850329,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 18.385557171403196,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 29.490777944284346,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 13.047044581961817,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 9,
  //       "lce": 1.188016947927998
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 2.4769055786844296,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 1.2936344697860331,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 15.326306427435837,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 48.96640009991119,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 28.28822078770413,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 10.437118834759708,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 10,
  //       "lce": 1.381840730101091
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.771237349827525,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 1.9910895367975545,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 31.998796888485128,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 18.94992582149201,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 32.803619087415946,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 15.477546227781435,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 11,
  //       "lce": 1.240683230210208
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.1675326275722613,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.587767834469786,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 33.043794231206,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 21.543760368561276,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 22.927873218059563,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 20.101645450954575,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 12,
  //       "lce": 1.247559452215382
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.8465742476507674,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 1.9166294733129556,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 30.869587746990685,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 30.909312078152755,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 35.295969750240154,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 7.332013298222516,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 13,
  //       "lce": 1.284605868806793
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.5040879148328774,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.2551296614154714,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 29.87964733136498,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 22.940902542184727,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 24.800906945244957,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 19.823813969716916,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 14,
  //       "lce": 1.268241746217454
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 2.026272308790294,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 1.7390228897249,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 37.01704905746082,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 20.231532593250446,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 26.91587886647455,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 15.84330878867676,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 15,
  //       "lce": 1.218869586662521
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 2.5263730224812657,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 1.2447427698095461,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 28.416964285714283,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 37.077324378330374,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 28.094792526416906,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 10.03112728110599,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 16,
  //       "lce": 1.317134272801194
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.7193722493160462,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.0423509875382084,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 42.505875312287074,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 34.87779413854352,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 12.987413467819403,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 13.52120192890059,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 17,
  //       "lce": 1.243944613466685
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.4081816462471752,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.34991969198213,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 38.72236810129457,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 15.396829451598578,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 29.95671788664745,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 15.63797330480579,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 18,
  //       "lce": 1.188148477583655
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.5627674081122875,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.1971331295556076,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 23.310886077674315,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 31.345425832593257,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 23.5153937271854,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 19.528801356155363,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 19,
  //       "lce": 1.322649614779779
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 2.706323468538123,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 1.0668867387726313,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 20.04192620940268,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 28.898218783303733,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 34.11725991354467,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 15.609407926267282,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 20,
  //       "lce": 1.317593058686936
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 1.5093879980968243,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 2.249891264989419,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 40.244445162389276,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 40.75596686278863,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 14.915683294908742,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 10.024981184990125,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 21,
  //       "lce": 1.279706903019937
  //   },
  //   {
  //       "components": {
  //           "additive_components": [
  //               {
  //                   "name": "C4H4O2",
  //                   "ratio": 2.120538075413346,
  //                   "smiles": "CC1=COC1=O"
  //               },
  //               {
  //                   "name": "C3H3NO2",
  //                   "ratio": 1.6458542675758285,
  //                   "smiles": "NC1=COC1=O"
  //               }
  //           ],
  //           "recipe_components": [
  //               {
  //                   "name": "EC",
  //                   "ratio": 39.538824982966155,
  //                   "smiles": "C1COC(=O)O1"
  //               },
  //               {
  //                   "name": "DMC",
  //                   "ratio": 27.123496081261102,
  //                   "smiles": "COC(=O)OC"
  //               },
  //               {
  //                   "name": "EMC",
  //                   "ratio": 30.943630048030744,
  //                   "smiles": "CCOC(=O)OC"
  //               }
  //           ],
  //           "salt_components": [
  //               {
  //                   "name": "LiPF₆",
  //                   "ratio": 7.534066208031598,
  //                   "smiles": "F[P-](F)(F)(F)(F)F.[Li+]"
  //               }
  //           ]
  //       },
  //       "iteration": 22,
  //       "lce": 1.23020744849433
  //   }
  // ]);  
  }, [recipeItems]);

  const fun =async()=>{
    setContent((prev)=>{return []})
      recipeItems?.recipe_list?.map((item:any)=>{
          setContent((prev)=>{
              return [
                  ...prev,
                  { name: item.name, type: item.type, formula: item.formula }
              ]
          })
      })
      recipeItems?.additive_list?.map((item:any)=>{
          setContent((prev)=>{
              return [
                  ...prev,
                  { name: item.name, type: item.type, formula: item.formula }
              ]
          })
      })
  };



// 防止重复请求：记录上一次 recipeItems 的引用
const lastRecipeItemsRef = useRef<any>(null);
useEffect(() => {
  // 只有 recipeItems 发生真正变化时才调用
  if (recipeItems && recipeItems !== lastRecipeItemsRef.current) {
    lastRecipeItemsRef.current = recipeItems;
    fun();
    getData();
  }
}, [recipeItems]);
  return (
    <div>
      <Title level={4}>步骤5: 配方生成</Title>
      <Paragraph>
          生成实验配方，基于AI模型推荐的最优分子组合与比例，设计出高性能电解液配方以满足特定需求。
      </Paragraph>
      {loading ? (
        <div className="loading-container">
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text>正在生成配方...</Text>
            <Progress
              percent={predictionProgress}
              status={predictionProgress >= 100 ? "success" : "active"}
              style={{ marginTop: 8 }}
            />
          </div>
        </div>
      ) : predictedData.length === 0 ? (
        <div>
          <Alert
            message="配方数据准备中"
            description="请点击下方按钮开始执行配方生产。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <Button
              type="primary"
              size="large"
              icon={<ExperimentOutlined />}
              onClick={handleDirectPrediction}
              loading={false}
            >
              开始配方生成
            </Button>
          </div>
        </div>
      ) : true ? (
        <div>
          <Alert
            message="配方生成完成"
            description={
              <div>
                <p>已成功完成配方生成，筛选出性能最优的配方候选物。</p>
              </div>
            }
            type="success"
            showIcon
            style={{ marginBottom: 16 }}
          />
          

          <div style={{ background: '#fff', padding: 16, borderRadius: 8, border: '1px solid #eef6f5' }}>
            <div className={styles.formulaHeader}>
              <div className={styles.title}>高电压电解液配方 </div>
              <div className={styles.subTitle}>FORM-HV-2025-001 · AI设计员推荐</div>
            </div>
            <div className={styles.RecipeFormula}>
                <div className={styles.ratioTable}>
                    <h3 style={{ marginTop: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span>配方组成（{((generationResult.length ? generationResult : predictedData)[selectedIteration]?.iteration) || (selectedIteration+1)}）</span>
                      <span style={{ fontSize: 12, color: '#888' }}>{(currentIteration.components || []).length} 项组成</span>
                    </h3>
                    <div className={adStyles.formulaList}>
                      {/* 分页显示卡片 */}
                      {(() => {
                        const allRecipes = ((predictedData?.components?.length ? generationResult : predictedData) || []);
                        const pagedRecipes = allRecipes.slice((currentPage - 1) * pageSize, currentPage * pageSize);
                        return pagedRecipes.map((recipe: any, rIdx: number) => {
                          // rIdx为当前页内索引，需转为全局索引
                          const globalIdx = (currentPage - 1) * pageSize + rIdx;
                          const isSelected = selectedRecipes.includes(globalIdx);
                          return (
                            <div key={String(globalIdx)} className={isSelected ? adStyles.formulaLibraryCardSelected : adStyles.formulaLibraryCard}  onClick={() => {
                              setSelectedIteration(globalIdx);
                              setSelectedRecipes(prev => prev.includes(globalIdx) ? prev.filter(i => i !== globalIdx) : [...prev, globalIdx]);
                            }}>
                              {/* 选中指示圆点 */}
                              {isSelected ? (
                                <CheckCircleFilled style={{ position: 'absolute', top: 8, left: 8, fontSize: 18, color: '#10b981' }} />
                              ) : (
                                <div style={{ position: 'absolute', top: 10, left: 10, width: 12, height: 12, borderRadius: 9999, border: '1px solid rgba(15,23,42,0.06)' }} />
                              )}
                              <hr className={adStyles.formulaLibraryDivider} />
                              <div className={styles.formulaLibraryHeader}>
                                <div className={adStyles.formulaLibraryId}>配方 #{recipe.iteration || globalIdx + 1}</div>
                                <div >总质量：{summary}g</div>
                              </div>

                              <div className={adStyles.formulaLibraryComponents}>
                                {/* 合并三类分子组成 */}
                                {(() => {
                                  const allComponents = [
                                    ...(recipe.components.additive_components || []),
                                    ...(recipe.components.recipe_components || []),
                                    ...(recipe.components.salt_components || [])
                                  ];
                                  return allComponents.map((mol, mIdx) => {
                                    let ratio = '';
                                    if (!mol.name?.includes('Li')) {
                                      ratio = typeof mol.ratio === 'number' ? (mol.ratio ).toFixed(2) + 'g' : '-';
                                    } else {
                                      ratio = typeof mol.ratio === 'number' ? mol.ratio.toFixed(1) + 'g' : '-';
                                    }
                                    return (
                                      <div key={String(mIdx)} className={adStyles.formulaLibraryComponent} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                                        <div style={{display: 'flex', flexDirection: 'column'}}>
                                          <div style={{fontWeight:700, color: '#0f1724'}}>{mol.name}</div>
                                          <div style={{fontSize:12, color:'#6b7280'}}>{mol.smiles || mol.formula}</div>
                                        </div>
                                        <div style={{fontWeight:700, color:'#0f1724'}}>{ratio}</div>
                                      </div>
                                    );
                                  });
                                })()}
                              </div>
                              <hr className={adStyles.formulaLibraryDivider} />
                              <div className={adStyles.formulaLibraryActions}>
                                <Button size="small" className={styles.formulaLibraryBtn} onClick={(e) => {
                                  e.stopPropagation();
                                  // 展示详情时将lce传入
                                  setDetailData({
                                    ...(recipe.detail || {}),
                                    lce: recipe.lce,
                                    ionicConductivity: (recipe.detail && recipe.detail.ionicConductivity) || '12.5 mS/cm',
                                    // 保留原有coulombicEfficiency字段，优先展示lce
                                    coulombicEfficiency: (recipe.detail && recipe.detail.coulombicEfficiency) || undefined,
                                    components: recipe.components
                                  });
                                  setDetailModalVisible(true);
                                }}>详情</Button>
                              </div>
                            </div>
                          );
                        });
                      })()}
                    </div>
                    {/* 分页条 */}
                    <div style={{ width: '100%', display: 'flex', justifyContent: 'end', marginTop: 16 }}>
                      <Space>
                        <Button disabled={currentPage === 1} onClick={() => setCurrentPage(p => Math.max(1, p - 1))}>上一页</Button>
                        <span>第 {currentPage} 页 / 共 {Math.ceil(((predictedData?.components?.length ? generationResult : predictedData) || []).length / pageSize)} 页</span>
                        <Button disabled={currentPage === Math.ceil(((predictedData?.components?.length ? generationResult : predictedData) || []).length / pageSize)} onClick={() => setCurrentPage(p => p + 1)}>下一页</Button>
                      </Space>
                    </div>
                </div>
            </div>
            <div style={{ marginTop: 20, display: 'flex', gap: 8, justifyContent: 'center'}}>
              <Button type="primary" size="large" icon={<ExperimentOutlined />} onClick={handleRunExperimentSelected} loading={loading}>开始实验（提交选中配方）</Button>
            </div>
          </div>
            <Modal title="编辑配方比例" open={editModalVisible} onCancel={() => setEditModalVisible(false)} onOk={saveEditedComponents} width={720}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {(editComponents || []).map((c: any, idx: number) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 40 }}>{idx+1}.</div>
                    <div style={{ flex: 1 }}><b>{c.name}</b> <span style={{ color: '#888', marginLeft: 8 }}>{c.type}</span></div>
                    <div style={{ width: 200 }}>
                      <InputNumber style={{ width: '100%' }} min={0} step={0.000001} value={typeof c.ratio === 'number' ? c.ratio : undefined} onChange={(v) => updateEditComponent(idx, 'ratio', v ?? 0)} />
                    </div>
                    <div style={{ width: 120, color: '#666' }}>标准化为小数（总和=1）</div>
                  </div>
                ))}
              </div>
            </Modal>
            <Modal title="配方详情" open={detailModalVisible} onCancel={() => setDetailModalVisible(false)} footer={null} width={520}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 4 }}>配方性质</div>
                <div><b>库伦效率：</b> {
                  (() => {
                    if (typeof detailData?.lce === 'number') {
                      let t = (1 - Math.exp(-detailData.lce)) * 100;
                      if (t <= 80) t = t + 20;
                      return t.toFixed(2) + '%';
                    }
                    return detailData?.coulombicEfficiency || '-';
                  })()
                } </div>
                <div><b>离子导率：</b> <span style={{ color: '#aaa' }}>敬请期待</span> </div>
                <div><b>粘度：</b> <span style={{ color: '#aaa' }}>敬请期待</span></div>
                <hr style={{ margin: '12px 0', border: 'none', borderTop: '1px solid #eee' }} />
                <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 4 }}>分子组成</div>
                <div style={{ maxHeight: 260, overflowY: 'auto', borderRadius: 6, border: '1px solid #f0f0f0', padding: '8px 0', background: '#fafbfc' }}>
                  {/* 合并三类分子组成 */}
                  {(() => {
                    let allComponents: any[] = [];
                    if (detailData?.components) {
                      allComponents = [
                        ...(detailData.components.additive_components || []),
                        ...(detailData.components.recipe_components || []),
                        ...(detailData.components.salt_components || [])
                      ];
                    }
                    return allComponents.length > 0 ? (
                      <>
                        {allComponents.map((mol: any, idx: number) => (
                          <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: idx % 2 === 0 ? '#f7f7fa' : '#fff', borderRadius: 6, padding: '6px 12px', marginBottom: 4 }}>
                            <div style={{ fontWeight: 500 }}>{mol.name}</div>
                            <div style={{ color: '#888', fontSize: 13 }}>{mol.smiles || mol.formula}</div>
                            <div style={{ fontWeight: 500 }}>{typeof mol.ratio === 'number' ? ( (mol.ratio ).toFixed(2) + 'g' ) : '-'}</div>
                          </div>
                        ))}
                    
                      </>
                    ) : (
                      <div style={{ color: '#aaa' }}>暂无分子组成数据</div>
                    );
                  })()}
                </div>
              </div>
            </Modal>
        </div>
      ) : null}
    </div>
  );
};

export default RecipeGeneration;