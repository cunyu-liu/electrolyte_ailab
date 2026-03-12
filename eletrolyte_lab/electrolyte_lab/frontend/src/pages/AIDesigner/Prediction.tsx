
import type { Dispatch, SetStateAction } from 'react';
import React, { useState, useEffect, useCallback,useRef } from 'react';
import styles from '../../css/Prediction.module.css';
import { Typography,  Spin, Progress, Alert, Button, Row, Col, Card, Statistic, Table, InputNumber, Input, Select, message, Space, Empty,Modal } from 'antd';
import { ExperimentOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { aiDesignerApi, molecularApi, literatureApi } from '../../services/api';
import {
  ParsedParameters,
  FormulaDataset,
  PredictedData,
  Formula
} from '../../types';
import MoleculeThreeViewer from '../../components/MoleculeThreeViewer';
const { Title, Paragraph, Text } = Typography;




type StepHistoryType = Record<number, any>;

const Prediction: React.FC<{ setCurrentStep?: (step: number) => void; setStepHistory?: Dispatch<SetStateAction<StepHistoryType>>; generatedMolecules?: any[]; setRecipeItems?: Dispatch<SetStateAction<any[]>> }> = ({ setCurrentStep, setStepHistory, generatedMolecules: incomingGeneratedMolecules, setRecipeItems }) => {
  const [loading, setLoading] = useState(false);
  const [predictionProgress, setPredictionProgress] = useState(0);
  const [predictedData, setPredictedData] = useState([] as any);
  const [viewerVisible, setViewerVisible] = useState(false);
  const [viewerSmiles, setViewerSmiles] = useState<string[]>([]);
  const openViewer = (smiles: string[] = []) => { setViewerSmiles(smiles.filter(Boolean)); setViewerVisible(true);console.log('打开3D视图，smiles:', smiles); };
  const closeViewer = () => { setViewerVisible(false); setViewerSmiles([]); };
  // 配方设计面板状态（类型优先：先选类型，再输入名称与数值）
  const [formulaType, setFormulaType] = useState<'salt' | 'solvent' | 'additive' | null>('salt');
  const [ingredientName, setIngredientName] = useState<string>('');
  const [ingredientValue, setIngredientValue] = useState<number | string | null>(null); // 盐使用浓度字符串，溶剂/添加剂使用百分比数字
  const [selectedIngredients, setSelectedIngredients] = useState<any[]>([]);
  const [electrolyteQuantity, setElectrolyteQuantity] = useState<number>(22);
  // 配方库视图与存储（前端临时存储）
  const [libraryView, setLibraryView] = useState<'design' | 'library'>('design');
  const initialSavedRecipes = [
    {
      id: 'FORM001',
      name: '标准电解液配方',
      type: 'AI推荐',
      components: [
        { name: 'EC', smiles: 'C1COC(=O)O1', ratio: 30 },
        { name: 'DMC', smiles: 'COC(=O)OC', ratio: 40 },
        { name: 'EMC', smiles: 'CCOC(=O)OC', ratio: 30 },
        { name: 'LiPF₆', smiles: 'F[P-](F)(F)(F)(F)F.[Li+]', ratio: 1.0},
      ],
      createdAt: '2025-01-15'
    },
    {
      id: 'FORM002',
      name: '低温电解液配方',
      type: 'AI推荐',
      components: [
        { name: 'FEC', smiles: 'O=C1OC(F)CO1', ratio: 10   },
        { name: 'EC', smiles: 'C1COC(=O)O1', ratio: 25 },
        { name: 'DEC', smiles: 'CCOC(=O)OCC', ratio: 65 },
        { name: 'LiFSI', smiles: 'O=S(=O)(NS(=O)(=O)CF3)CF3.[Li+]', ratio: 1.2 }
      ],
      createdAt: '2025-01-18'
    },
    {
      id: 'FORM003',
      name: '宽温电解液配方',
      type: 'AI推荐',
      components: [
        { name: 'PC', smiles: 'O=C1OCCCO1', ratio: 50 },
        { name: 'EMC', smiles: 'CCOC(=O)OC', ratio: 50 },
        { name: 'LiTFSI', smiles: 'O=S(=O)(NS(=O)(=O)C(F)(F)F)C(F)(F)F.[Li+]', ratio: 0.8 },
        { name: 'VC', smiles: 'O=C1OC=CC1', ratio: 2 }
      ],
      createdAt: '2025-01-20'
    }
  ];
  const [currentRecipe, setCurrentRecipe] = useState<any | null>(null);
  const [savedRecipes, setSavedRecipes] = useState<Array<any>>(initialSavedRecipes);
  const [currentMolecule, setCurrentMolecule] = useState<any | null>(null);
  //筛选属性列表
  const propertyFilters = [
    { key: 'Binding energy (eV)_pred', label: '结合能', unit: 'eV', minAllowed: -100, step: 0.01 },
    { key: 'Dielectric constant of solvents_pred', label: '介电常数', unit: '', minAllowed: 0, step: 0.01 },
    // 扩散系数以 1e-9 为单位显示（方便输入），输入表示为实际值 * 1e9
    { key: 'Diffusivity of solvens (m^2/s)_pred', label: '扩散系数', unit: 'e-9 m²/s', minAllowed: 0, step: 0.01, scale: 1e9 },
    { key: 'Formation energy in solvent (eV/atom)_pred', label: '形成能', unit: 'eV/atom', minAllowed: -100, step: 0.01 },
    { key: 'HOMO_sol (eV)_pred', label: 'HOMO', unit: 'eV', minAllowed: -100, step: 0.01 },
    { key: 'LUMO_sol (eV)_pred', label: 'LUMO', unit: 'eV', minAllowed: -100, step: 0.01 },
    { key: 'Viscosity of solvents (mPa s)_pred', label:'黏度', unit:'mPa·s' ,minAllowed : 0 ,step : 1},
    { key : "Transference number of Li_pred" ,label : "离子迁移数" ,unit : "" ,minAllowed : 0 ,step : 1},
  ];
  // 过滤器状态（编辑中的值）
  const [filterValues, setFilterValues] = useState<Record<string, { min?: number | null; max?: number | null }>>(() => {
    const init: Record<string, { min?: number | null; max?: number | null }> = {};
    propertyFilters.forEach(p => { init[p.key] = { min: null, max: null }; });
    return init;
  });
  // 已应用的过滤器（仅在点击“应用筛选”后生效）
  const [appliedFilters, setAppliedFilters] = useState<typeof filterValues>(() => {
    const init: Record<string, { min?: number | null; max?: number | null }> = {};
    propertyFilters.forEach(p => { init[p.key] = { min: null, max: null }; });
    return init;
  });
  //Table数据
  const sampleMolecules: any[] = (Array.isArray(predictedData)? predictedData: []).map((p: any, i: number) => {
    const smiles = p.SMILES || p.smiles || p.smiles_notation || p.SMILES_f || '';
    const name = p.name || smiles || `Mol${i + 1}`;
    const viscosity = p['Viscosity of electrolytes (mPa s)_pred'] ?? p['Viscosity of solvents (mPa s)_pred'] ?? p.viscosity ?? null;
    const conductivity = p['Conductivity (S/cm)_pred'] ?? p.conductivity ?? null;
    const transference = p['Transference number of Li_pred'] ?? p.transference ?? null;
    return {
      id: `R${String(i + 1).padStart(3, '0')}`,
      name,
      type: p.component_type || p.type || '预测分子',
      viscosity,
      mp: p.molecular_properties?.molecular_weight ?? null,
      bp: null,
      conductivity,
      decomposition: null,
      flash: null,
      density: null,
      smiles: smiles,
      smiles_notation: smiles,
      transference,
      predicted: p
    };
  });
  const columns: ColumnsType<any> = [
     {
      title: '分子式',
      key: 'MolecularFormula',
      width: 180,
      render: (_: any, record: any) => {
        const val = incomingGeneratedMolecules.find(m=>m.SMILES==record.predicted?.['SMILES'])?.formula;
        return val ;
      }
    },
    {
      title: '结合能 (eV)',
      key: 'Binding',
      width: 180,
      render: (_: any, record: any) => {
        const val = record.predicted?.['Binding energy (eV)_pred'] ?? record.predicted?.['Viscosity of solvents (mPa s)_pred'] ?? record.viscosity;
        return val == null ? '-' : Number(val).toFixed(2);
      }
    },
    {
      title: '介电常数',
      key: 'Dielectric constant of solvents_pred',
      width: 180,
      render: (_: any, record: any) => {
        const val = record.predicted?.['Dielectric constant of solvents_pred'];
        return val == null ? '-' : Number(val).toFixed(2);
      }
    },
    {
      title: '扩散系数 (m²/s)',
      key: 'Diffusivity of solvens (m^2/s)_pred',
      width: 180,
      render: (_: any, record: any) => {
        const val = record.predicted?.['Diffusivity of solvens (m^2/s)_pred'] ?? record.conductivity;
        return val == null ? '-' : Number(val).toExponential(2);
      }
    },
    {
      title: '形成能 (eV/atom)',
      key: 'Formation energy in solvent (eV/atom)_pred',
      width: 180,
      render: (_: any, record: any) => {
        const val = record.predicted?.['Formation energy in solvent (eV/atom)_pred'] ?? record.transference;
        return val == null ? '-' : Number(val).toFixed(2);
      }
    },
  
    {
      title: 'HOMO (eV)',
      key: 'HOMO_sol (eV)_pred',
      width: 180,
      render: (_: any, record: any) => {
        const val = record.predicted?.['HOMO_sol (eV)_pred'];
        return val == null ? '-' : Number(val).toFixed(2);
      }
    },
    {
      title: 'LUMO (eV)',
      key: 'LUMO_sol (eV)_pred',
      width: 180,
      render: (_: any, record: any) => {
        const val = record.predicted?.['LUMO_sol (eV)_pred'];
        return val == null ? '-' : Number(val).toFixed(2);
      }
    },
     {
      title: '黏度 (mPa s)',
      key: 'Viscosity of solvents (mPa s)_pred',
      width: 180,
      render: (_: any, record: any) => {
        const val = record.predicted?.['Viscosity of solvents (mPa s)_pred'];
        return val == null ? '-' : Number(val).toFixed(2);
      }
    },
     {
      title: '离子迁移数',
      key: 'Transference',
      width: 180,
      render: (_: any, record: any) => {
        const val = record.predicted?.['Transference number of Li_pred'];
        return val == null ? '-' : Number(val).toFixed(2);
      }
    },
    {
      title: '操作', key: 'action', width: 220, render: (_: any, record: any) => (
        <div>
          <Button className={styles.actionBtn} size="small" onClick={() => {
            const mapType = record.type === '锂盐' ? 'salt' : record.type === '溶剂' ? 'solvent' : 'additive';
            const val = incomingGeneratedMolecules.find(m=>m.SMILES==record.predicted?.['SMILES'])?.formula;
            setFormulaType(mapType as any);
            setCurrentMolecule(record);
            setIngredientName(val);
            message.success(`已选择 ${val}，请设置比例/浓度`);
          }}>选择</Button>
          <Button className={styles.actionBtn} size="small" onClick={() => {
            openViewer([record.smiles || record.smiles_notation || record.predicted?.['SMILES']]);
            setCurrentRecipe(record);
          }}>详情</Button>
        </div>
      )
    }
  ];
  const handleFilterChange = (key: string, side: 'min' | 'max', val: number | null) => {
    setFilterValues(prev => ({ ...prev, [key]: { ...prev[key], [side]: val } }));
  };

  const handleResetFilters = () => {
    const reset: Record<string, { min?: number | null; max?: number | null }> = {};
    propertyFilters.forEach(p => { reset[p.key] = { min: null, max: null }; });
    setFilterValues(reset);
    setAppliedFilters(reset);
    message.success('筛选条件已重置');
  };

  const handleApplyFilters = () => {
    setAppliedFilters(filterValues);
    message.success('已应用筛选条件');
  };
   // 3. 直接预测 - 跳过数据挖掘，直接进行分子生成和预测
  const handleDirectPrediction = async () => {
     runPrediction();
  };
  const addIngredient = () => {
    if (!formulaType || !ingredientName) {
      message.error('请先选择类型并输入名称');
      return;
    }
    console.log(currentMolecule)
    // 标记为手动添加
    if (formulaType === 'salt') {
      setSelectedIngredients(prev => [...prev, { type: 'salt', name: ingredientName,smiles:'', concentration: Number(ingredientValue) || '', origin: 'manual' }]);
    } else {
      setSelectedIngredients(prev => [...prev, { type: formulaType, name: ingredientName,smiles:currentMolecule.smiles||'', percent: Number(ingredientValue) || 0, origin: 'manual' }]);
    }

    setIngredientName('');
    setIngredientValue(null);
  };
  const removeIngredient = (index: number) => {
    setSelectedIngredients(prev => prev.filter((_, i) => i !== index));
  };

  const saveRecipe = () => {
    if (!selectedIngredients || selectedIngredients.length === 0) {
      message.error('尚未选择任何分子，无法保存配方');
      return;
    }
    const newRecipe = {
      id: Date.now(),
      name: `配方 ${savedRecipes.length + 1}`,
      components: selectedIngredients,
      createdAt: new Date().toISOString()
    };
    setSavedRecipes((prev) => [newRecipe, ...prev]);
    // 切换到配方库并清空当前配方（可选行为）
    clearFormula();
    setLibraryView('library');
    message.success('配方已保存并已切换到配方库（未持久化）');
  };
  
  const loadRecipe = (recipe: { components: any[] }) => {
    if (!recipe || !recipe.components) return;
    const mapped = recipe.components.map((c: any) => {
      const ratioRaw = c.ratio;
      const ratioStr = String(ratioRaw || '');
      if (ratioStr.includes('M')) {
        return { type: 'salt', name: c.name, concentration: ratioStr, ratio: ratioRaw, smiles: c.smiles, origin: 'recipe' };
      }
      // 保留 ratio 字段，percent 仅用于显示
      return { type: 'solvent', name: c.name, percent: ratioStr, ratio: ratioRaw, smiles: c.smiles, origin: 'recipe' };
    });
    setSelectedIngredients(mapped);
  };
  
  const deleteRecipe = (id: number) => {
    setSavedRecipes((prev) => prev.filter((r) => r.id !== id));
    message.success('已删除配方');
  };
  const clearFormula = () => setSelectedIngredients([]);
  // 生成配方最终配方
  const handleGenerateFormula = async () => {
    // 将当前选中的配方组件（selectedIngredients）作为生成分子传入父组件（如果有提供 setter）
    try {
      const parseRatio = (val: any): number | null => {
        if (val == null) return null;
        const s = String(val).trim();
        if (s.endsWith('%')) {
          const n = parseFloat(s.replace('%', ''));
          return Number.isFinite(n) ? n : null;
        }
        const n = parseFloat(s);
        return Number.isFinite(n) ? n : null;
      };

      // recipe_list: 来自选中且 origin==='recipe' 的项（优先），若没有则尝试从 savedRecipes 中取全部已保存配方
      const recipe_list: Array<{ name: string; smiles: string; ratio: number | null }> = [];
      const recipeItems = selectedIngredients.filter(si => si.origin === 'recipe');
      let quality = 0;
      if (recipeItems.length > 0) {
        recipeItems.forEach((r: any) => {
          if(!r.name.includes('Li')){quality+=r.ratio}
        });
      } else if (savedRecipes && savedRecipes.length > 0) {
        const defaultRecipe = savedRecipes[0];
        (defaultRecipe.components || []).forEach((c: any) => {
          if(!c.name.includes('Li')){quality+=c.ratio}
        });
      }
      if (recipeItems.length > 0) {
        recipeItems.forEach((r: any) => {
          recipe_list.push({ name: r.name, smiles: r.smiles, ratio: r.percent/quality*100 ||r.ratio/quality*100 });
        });
      } else if (savedRecipes && savedRecipes.length > 0) {
        const defaultRecipe = savedRecipes[0];
        (defaultRecipe.components || []).forEach((c: any) => {
          recipe_list.push({ name: c.name, smiles: c.smiles, ratio: c.ratio/quality*100|| c.percent/quality*100});
        });
      }
      
      // additive_list: 来自手动添加或类型为 additive 的 selectedIngredients
      const additive_list: Array<{ name: string; smiles: string; ratio: number | null }> = [];
      let quality1 = 0;
      console.log('准备生成配方，selectedIngredients:', selectedIngredients);
      selectedIngredients.forEach((s: any) => {
        if (s.origin === 'manual' || s.type === 'additive') {
          quality1 += s.percent;
        }
      });
      selectedIngredients.forEach((s: any) => {
        if (s.origin === 'manual' || s.type === 'additive') {
          additive_list.push({ name: s.name, smiles: s.smiles, ratio:s.percent/quality1*100 });
        }
      });
      const payload = {
        recipe_list,
        additive_list,
        electrolyte_quantity: electrolyteQuantity || 22,
        quality,
        additive_range: quality1/quality || 0
      };

      if (setRecipeItems) {
        console.log('准备传递生成配方 payload：', payload);
        setRecipeItems(payload as any);
      }
    } catch (e) {
      console.warn('准备传递生成分子时出错，仍将跳转：', e);
    }

    // 跳转到下一界面
    setCurrentStep && setCurrentStep(4);
  };
// 当父组件传入 generatedMolecules 时，自动触发高通量性质预测请求
  let progressInterval: number | undefined;
  let cancelled = false;
  const runPrediction = useCallback(async () => {
    if (loading) return;
    const moleculesToUse = (incomingGeneratedMolecules && incomingGeneratedMolecules.length) ? incomingGeneratedMolecules : [];
    // 如果没有分子数据，不执行预测
    if (moleculesToUse.length === 0) {
      console.log('没有分子数据，跳过预测');
      return;
    }
    try {
      setLoading(true);
      setPredictionProgress(0);
      console.log('开始性质预测，分子数量:', moleculesToUse.length);
      // 解析smiles列表
      const smilesList = moleculesToUse
        .map((m: any) => m.smiles_notation || m.smiles || m.SMILES || m.smilesNotation)
        .filter((s: any) => s && typeof s === 'string' && s.trim());
      // 如果smiles列表为空，不执行API调用
      if (smilesList.length === 0) {
        console.log('没有有效的SMILES数据，跳过API调用');
        setLoading(false);
        return;
      }
      // 发送请求
      const predictResponse = await aiDesignerApi.predictProperties({ smiles_list: smilesList });
      setPredictionProgress(100);
      if (predictResponse && predictResponse.success) {
        const predicted = predictResponse.result_properties;
        console.log('预测结果:', predicted);
        setPredictedData(predicted);
        // 保存步骤历史
        if (setStepHistory) {
          setStepHistory(prev => ({
            ...prev,
            3: {
              title: '性质预测',
              description: '对分子进行高通量性质预测并筛选最优分子',
              timestamp: new Date().toISOString(),
              data: predicted,
              input: { molecules: moleculesToUse }
            }
          }));
        }
        const summary = `预测完成！从 ${predicted?.total_predictions || 0} 个分子中筛选出 ${predicted?.selected_count || 0} 个最优分子`;
        message.success(summary);
      } else {
        message.error('预测失败：' + (predictResponse?.message || '未知错误'));
      }
    } catch (error: any) {
      console.error('性质预测失败:', error);
      message.error(`性质预测失败：${error?.message || '请重试'}`);
    } finally {
      setLoading(false);
    } 

  //   setPredictedData([
  //   {
  //     "Binding energy (eV)_pred": -1.1261444091796875,
  //     "Binding energy (eV)_targ": 0.0,
  //     "Conductivity (S/cm)_pred": 0.0001251025731273,
  //     "Conductivity (S/cm)_targ": 0.0,
  //     "Dielectric constant of electrolytes_pred": 12.940051772377709,
  //     "Dielectric constant of electrolytes_targ": 0.0,
  //     "Dielectric constant of solvents_pred": 5.68289344960993,
  //     "Dielectric constant of solvents_targ": 0.0,
  //     "Diffusivity of FSI (m^2/s)_pred": -7.486589812734999e-09,
  //     "Diffusivity of FSI (m^2/s)_targ": 0.0,
  //     "Diffusivity of Li (m^2/s)_pred": 2.1202545012628932e-08,
  //     "Diffusivity of Li (m^2/s)_targ": 0.0,
  //     "Diffusivity of solvens (m^2/s)_pred": 1.0464815987502748e-07,
  //     "Diffusivity of solvens (m^2/s)_targ": 0.0,
  //     "Formation energy in solvent (eV/atom)_pred": -0.3333155214786529,
  //     "Formation energy in solvent (eV/atom)_targ": 0.0,
  //     "Formation energy in vaccum (eV/atom)_pred": -0.3015894971110604,
  //     "Formation energy in vaccum (eV/atom)_targ": 0.0,
  //     "HOMO change (eV)_pred": -2.230796510523016,
  //     "HOMO change (eV)_targ": 0.0,
  //     "HOMO_cls (eV)_pred": -10.248859492215244,
  //     "HOMO_cls (eV)_targ": 0.0,
  //     "HOMO_sol (eV)_pred": -8.060010086406361,
  //     "HOMO_sol (eV)_targ": 0.0,
  //     "LUMO change (eV)_pred": -2.8937066251581367,
  //     "LUMO change (eV)_targ": 0.0,
  //     "LUMO_cls (eV)_pred": -3.266301740299572,
  //     "LUMO_cls (eV)_targ": 0.0,
  //     "LUMO_sol (eV)_pred": -0.0890298539941961,
  //     "LUMO_sol (eV)_targ": 0.0,
  //     "SMILES": "CC1=CC(=O)O1",
  //     "Similarity of solvents_pred": 0.5841730291193182,
  //     "Similarity of solvents_targ": 0.0,
  //     "Transference number of Li_pred": 0.4927232319658453,
  //     "Transference number of Li_targ": 0.0,
  //     "Viscosity of electrolytes (mPa s)_pred": 14.989448807456276,
  //     "Viscosity of electrolytes (mPa s)_targ": 0.0,
  //     "Viscosity of solvents (mPa s)_pred": 15.68048147721724,
  //     "Viscosity of solvents (mPa s)_targ": 0.0
  //   },
  //   {
  //     "Binding energy (eV)_pred": -0.8476771278814836,
  //     "Binding energy (eV)_targ": 0.0,
  //     "Conductivity (S/cm)_pred": 0.0001563776935323,
  //     "Conductivity (S/cm)_targ": 0.0,
  //     "Dielectric constant of electrolytes_pred": 10.348656741055576,
  //     "Dielectric constant of electrolytes_targ": 0.0,
  //     "Dielectric constant of solvents_pred": 9.51225670901212,
  //     "Dielectric constant of solvents_targ": 0.0,
  //     "Diffusivity of FSI (m^2/s)_pred": -5.119597352115141e-09,
  //     "Diffusivity of FSI (m^2/s)_targ": 0.0,
  //     "Diffusivity of Li (m^2/s)_pred": 1.6232845209432613e-08,
  //     "Diffusivity of Li (m^2/s)_targ": 0.0,
  //     "Diffusivity of solvens (m^2/s)_pred": -3.123492058937865e-08,
  //     "Diffusivity of solvens (m^2/s)_targ": 0.0,
  //     "Formation energy in solvent (eV/atom)_pred": -0.2776135016571391,
  //     "Formation energy in solvent (eV/atom)_targ": 0.0,
  //     "Formation energy in vaccum (eV/atom)_pred": -0.2395739230242642,
  //     "Formation energy in vaccum (eV/atom)_targ": 0.0,
  //     "HOMO change (eV)_pred": -1.692881399934942,
  //     "HOMO change (eV)_targ": 0.0,
  //     "HOMO_cls (eV)_pred": -9.28760103745894,
  //     "HOMO_cls (eV)_targ": 0.0,
  //     "HOMO_sol (eV)_pred": -7.60207596692172,
  //     "HOMO_sol (eV)_targ": 0.0,
  //     "LUMO change (eV)_pred": -1.5783838900652798,
  //     "LUMO change (eV)_targ": 0.0,
  //     "LUMO_cls (eV)_pred": -1.31784019686959,
  //     "LUMO_cls (eV)_targ": 0.0,
  //     "LUMO_sol (eV)_pred": 0.3034490130164406,
  //     "LUMO_sol (eV)_targ": 0.0,
  //     "SMILES": "CC1=COC1=O",
  //     "Similarity of solvents_pred": 0.5983051332560453,
  //     "Similarity of solvents_targ": 0.0,
  //     "Transference number of Li_pred": 0.4985936419530348,
  //     "Transference number of Li_targ": 0.0,
  //     "Viscosity of electrolytes (mPa s)_pred": 10.356545968489211,
  //     "Viscosity of electrolytes (mPa s)_targ": 0.0,
  //     "Viscosity of solvents (mPa s)_pred": 7.440659609707919,
  //     "Viscosity of solvents (mPa s)_targ": 0.0
  //   },
  //   {
  //     "Binding energy (eV)_pred": -0.9627332470633768,
  //     "Binding energy (eV)_targ": 0.0,
  //     "Conductivity (S/cm)_pred": 0.0001248871875842,
  //     "Conductivity (S/cm)_targ": 0.0,
  //     "Dielectric constant of electrolytes_pred": 13.857956712896174,
  //     "Dielectric constant of electrolytes_targ": 0.0,
  //     "Dielectric constant of solvents_pred": 10.027972654862838,
  //     "Dielectric constant of solvents_targ": 0.0,
  //     "Diffusivity of FSI (m^2/s)_pred": -1.3399347247917089e-08,
  //     "Diffusivity of FSI (m^2/s)_targ": 0.0,
  //     "Diffusivity of Li (m^2/s)_pred": 2.7232690607609748e-08,
  //     "Diffusivity of Li (m^2/s)_targ": 0.0,
  //     "Diffusivity of solvens (m^2/s)_pred": -6.019794214621883e-08,
  //     "Diffusivity of solvens (m^2/s)_targ": 0.0,
  //     "Formation energy in solvent (eV/atom)_pred": -0.490620344877243,
  //     "Formation energy in solvent (eV/atom)_targ": 0.0,
  //     "Formation energy in vaccum (eV/atom)_pred": -0.4649472615935586,
  //     "Formation energy in vaccum (eV/atom)_targ": 0.0,
  //     "HOMO change (eV)_pred": -1.98726224899292,
  //     "HOMO change (eV)_targ": 0.0,
  //     "HOMO_cls (eV)_pred": -9.95476705377752,
  //     "HOMO_cls (eV)_targ": 0.0,
  //     "HOMO_sol (eV)_pred": -8.075216423381459,
  //     "HOMO_sol (eV)_targ": 0.0,
  //     "LUMO change (eV)_pred": -2.4954327019778164,
  //     "LUMO change (eV)_targ": 0.0,
  //     "LUMO_cls (eV)_pred": -2.8198802037672563,
  //     "LUMO_cls (eV)_targ": 0.0,
  //     "LUMO_sol (eV)_pred": -0.2358846339312466,
  //     "LUMO_sol (eV)_targ": 0.0,
  //     "SMILES": "NC1=COC1=O",
  //     "Similarity of solvents_pred": 0.4720409918915141,
  //     "Similarity of solvents_targ": 0.0,
  //     "Transference number of Li_pred": 0.5032977082512595,
  //     "Transference number of Li_targ": 0.0,
  //     "Viscosity of electrolytes (mPa s)_pred": 15.091103120283648,
  //     "Viscosity of electrolytes (mPa s)_targ": 0.0,
  //     "Viscosity of solvents (mPa s)_pred": 19.273723775690254,
  //     "Viscosity of solvents (mPa s)_targ": 0.0
  //   },
  //   {
  //     "Binding energy (eV)_pred": -1.3694935928691516,
  //     "Binding energy (eV)_targ": 0.0,
  //     "Conductivity (S/cm)_pred": 7.538330497812818e-05,
  //     "Conductivity (S/cm)_targ": 0.0,
  //     "Dielectric constant of electrolytes_pred": 6.6464127844030205,
  //     "Dielectric constant of electrolytes_targ": 0.0,
  //     "Dielectric constant of solvents_pred": 4.037384726784446,
  //     "Dielectric constant of solvents_targ": 0.0,
  //     "Diffusivity of FSI (m^2/s)_pred": -2.7282448139038188e-08,
  //     "Diffusivity of FSI (m^2/s)_targ": 0.0,
  //     "Diffusivity of Li (m^2/s)_pred": 5.022062361929743e-10,
  //     "Diffusivity of Li (m^2/s)_targ": 0.0,
  //     "Diffusivity of solvens (m^2/s)_pred": 1.7138169606699774e-07,
  //     "Diffusivity of solvens (m^2/s)_targ": 0.0,
  //     "Formation energy in solvent (eV/atom)_pred": -0.8037399757992137,
  //     "Formation energy in solvent (eV/atom)_targ": 0.0,
  //     "Formation energy in vaccum (eV/atom)_pred": -0.7506626898592169,
  //     "Formation energy in vaccum (eV/atom)_targ": 0.0,
  //     "HOMO change (eV)_pred": -2.033455729484558,
  //     "HOMO change (eV)_targ": 0.0,
  //     "HOMO_cls (eV)_pred": -10.371540069580078,
  //     "HOMO_cls (eV)_targ": 0.0,
  //     "HOMO_sol (eV)_pred": -8.32270336151123,
  //     "HOMO_sol (eV)_targ": 0.0,
  //     "LUMO change (eV)_pred": -3.2972463911229912,
  //     "LUMO change (eV)_targ": 0.0,
  //     "LUMO_cls (eV)_pred": -4.555602073669434,
  //     "LUMO_cls (eV)_targ": 0.0,
  //     "LUMO_sol (eV)_pred": -1.0826759663495151,
  //     "LUMO_sol (eV)_targ": 0.0,
  //     "SMILES": "O=C1C=C(O)O1",
  //     "Similarity of solvents_pred": 0.4968491413376548,
  //     "Similarity of solvents_targ": 0.0,
  //     "Transference number of Li_pred": 0.5043658857995813,
  //     "Transference number of Li_targ": 0.0,
  //     "Viscosity of electrolytes (mPa s)_pred": 43.810956087979406,
  //     "Viscosity of electrolytes (mPa s)_targ": 0.0,
  //     "Viscosity of solvents (mPa s)_pred": 39.938912478360265,
  //     "Viscosity of solvents (mPa s)_targ": 0.0
  //   },
  //   {
  //     "Binding energy (eV)_pred": -1.1015413457697087,
  //     "Binding energy (eV)_targ": 0.0,
  //     "Conductivity (S/cm)_pred": 5.169071598422968e-05,
  //     "Conductivity (S/cm)_targ": 0.0,
  //     "Dielectric constant of electrolytes_pred": 5.815240123055198,
  //     "Dielectric constant of electrolytes_targ": 0.0,
  //     "Dielectric constant of solvents_pred": 3.708328593860973,
  //     "Dielectric constant of solvents_targ": 0.0,
  //     "Diffusivity of FSI (m^2/s)_pred": -2.0011741435672033e-08,
  //     "Diffusivity of FSI (m^2/s)_targ": 0.0,
  //     "Diffusivity of Li (m^2/s)_pred": -7.422838747701958e-09,
  //     "Diffusivity of Li (m^2/s)_targ": 0.0,
  //     "Diffusivity of solvens (m^2/s)_pred": -2.438967369884763e-07,
  //     "Diffusivity of solvens (m^2/s)_targ": 0.0,
  //     "Formation energy in solvent (eV/atom)_pred": -0.7809633666818793,
  //     "Formation energy in solvent (eV/atom)_targ": 0.0,
  //     "Formation energy in vaccum (eV/atom)_pred": -0.7380394773049788,
  //     "Formation energy in vaccum (eV/atom)_targ": 0.0,
  //     "HOMO change (eV)_pred": -2.521327950737693,
  //     "HOMO change (eV)_targ": 0.0,
  //     "HOMO_cls (eV)_pred": -10.5904784636064,
  //     "HOMO_cls (eV)_targ": 0.0,
  //     "HOMO_sol (eV)_pred": -8.164922367442738,
  //     "HOMO_sol (eV)_targ": 0.0,
  //     "LUMO change (eV)_pred": -3.0794197646054355,
  //     "LUMO change (eV)_targ": 0.0,
  //     "LUMO_cls (eV)_pred": -4.052479397166859,
  //     "LUMO_cls (eV)_targ": 0.0,
  //     "LUMO_sol (eV)_pred": -0.9931849024512552,
  //     "LUMO_sol (eV)_targ": 0.0,
  //     "SMILES": "O=C1CC(F)(F)O1",
  //     "Similarity of solvents_pred": 0.5604760538447987,
  //     "Similarity of solvents_targ": 0.0,
  //     "Transference number of Li_pred": 0.4889704503796317,
  //     "Transference number of Li_targ": 0.0,
  //     "Viscosity of electrolytes (mPa s)_pred": 33.06278922341087,
  //     "Viscosity of electrolytes (mPa s)_targ": 0.0,
  //     "Viscosity of solvents (mPa s)_pred": 26.123701268976387,
  //     "Viscosity of solvents (mPa s)_targ": 0.0
  //   },
  //   {
  //     "Binding energy (eV)_pred": -0.8788047324527394,
  //     "Binding energy (eV)_targ": 0.0,
  //     "Conductivity (S/cm)_pred": 1.6789462692527607e-05,
  //     "Conductivity (S/cm)_targ": 0.0,
  //     "Dielectric constant of electrolytes_pred": 5.468176798387007,
  //     "Dielectric constant of electrolytes_targ": 0.0,
  //     "Dielectric constant of solvents_pred": 2.972921848297119,
  //     "Dielectric constant of solvents_targ": 0.0,
  //     "Diffusivity of FSI (m^2/s)_pred": -2.8454002790309376e-08,
  //     "Diffusivity of FSI (m^2/s)_targ": 0.0,
  //     "Diffusivity of Li (m^2/s)_pred": -9.494063878502278e-09,
  //     "Diffusivity of Li (m^2/s)_targ": 0.0,
  //     "Diffusivity of solvens (m^2/s)_pred": -1.5091005810642277e-07,
  //     "Diffusivity of solvens (m^2/s)_targ": 0.0,
  //     "Formation energy in solvent (eV/atom)_pred": -0.8229347792538729,
  //     "Formation energy in solvent (eV/atom)_targ": 0.0,
  //     "Formation energy in vaccum (eV/atom)_pred": -0.7716159712184559,
  //     "Formation energy in vaccum (eV/atom)_targ": 0.0,
  //     "HOMO change (eV)_pred": -2.399558890949596,
  //     "HOMO change (eV)_targ": 0.0,
  //     "HOMO_cls (eV)_pred": -10.413376287980514,
  //     "HOMO_cls (eV)_targ": 0.0,
  //     "HOMO_sol (eV)_pred": -8.160563295537775,
  //     "HOMO_sol (eV)_targ": 0.0,
  //     "LUMO change (eV)_pred": -2.797134659507058,
  //     "LUMO change (eV)_targ": 0.0,
  //     "LUMO_cls (eV)_pred": -3.6098673993890937,
  //     "LUMO_cls (eV)_targ": 0.0,
  //     "LUMO_sol (eV)_pred": -0.929138953035528,
  //     "LUMO_sol (eV)_targ": 0.0,
  //     "SMILES": "O=C1OC(F)C1F",
  //     "Similarity of solvents_pred": 0.5527556701139971,
  //     "Similarity of solvents_targ": 0.0,
  //     "Transference number of Li_pred": 0.4801634739745747,
  //     "Transference number of Li_targ": 0.0,
  //     "Viscosity of electrolytes (mPa s)_pred": 58.57589132135565,
  //     "Viscosity of electrolytes (mPa s)_targ": 0.0,
  //     "Viscosity of solvents (mPa s)_pred": 55.35064766623757,
  //     "Viscosity of solvents (mPa s)_targ": 0.0
  //   },
  //   {
  //     "Binding energy (eV)_pred": -0.8462072881785306,
  //     "Binding energy (eV)_targ": 0.0,
  //     "Conductivity (S/cm)_pred": 4.320012786510316e-05,
  //     "Conductivity (S/cm)_targ": 0.0,
  //     "Dielectric constant of electrolytes_pred": 5.887219515713778,
  //     "Dielectric constant of electrolytes_targ": 0.0,
  //     "Dielectric constant of solvents_pred": 4.770920623432506,
  //     "Dielectric constant of solvents_targ": 0.0,
  //     "Diffusivity of FSI (m^2/s)_pred": -2.6686971703200738e-08,
  //     "Diffusivity of FSI (m^2/s)_targ": 0.0,
  //     "Diffusivity of Li (m^2/s)_pred": 1.6211686377170572e-08,
  //     "Diffusivity of Li (m^2/s)_targ": 0.0,
  //     "Diffusivity of solvens (m^2/s)_pred": 8.573735693124201e-08,
  //     "Diffusivity of solvens (m^2/s)_targ": 0.0,
  //     "Formation energy in solvent (eV/atom)_pred": -0.7018533565781333,
  //     "Formation energy in solvent (eV/atom)_targ": 0.0,
  //     "Formation energy in vaccum (eV/atom)_pred": -0.6564135226336393,
  //     "Formation energy in vaccum (eV/atom)_targ": 0.0,
  //     "HOMO change (eV)_pred": -2.5633068951693447,
  //     "HOMO change (eV)_targ": 0.0,
  //     "HOMO_cls (eV)_pred": -10.556796420704234,
  //     "HOMO_cls (eV)_targ": 0.0,
  //     "HOMO_sol (eV)_pred": -8.194976893338291,
  //     "HOMO_sol (eV)_targ": 0.0,
  //     "LUMO change (eV)_pred": -2.6594612164930864,
  //     "LUMO change (eV)_targ": 0.0,
  //     "LUMO_cls (eV)_pred": -3.502500880848278,
  //     "LUMO_cls (eV)_targ": 0.0,
  //     "LUMO_sol (eV)_pred": -0.9935271631587635,
  //     "LUMO_sol (eV)_targ": 0.0,
  //     "SMILES": "O=C1OC=C1O",
  //     "Similarity of solvents_pred": 0.4226849566806446,
  //     "Similarity of solvents_targ": 0.0,
  //     "Transference number of Li_pred": 0.4660305164077065,
  //     "Transference number of Li_targ": 0.0,
  //     "Viscosity of electrolytes (mPa s)_pred": 43.05518445101652,
  //     "Viscosity of electrolytes (mPa s)_targ": 0.0,
  //     "Viscosity of solvents (mPa s)_pred": 65.88989812677556,
  //     "Viscosity of solvents (mPa s)_targ": 0.0
  //   }
  // ]);
  }, [incomingGeneratedMolecules]);

  // 防止重复预测：记录上一次预测的分子数据引用
  const lastPredictedMoleculesRef = useRef<any[]>([]);
  useEffect(() => {
    // 只在分子数据有变化且未预测过时才触发
    
    if (
      incomingGeneratedMolecules &&
      incomingGeneratedMolecules.length > 0 &&
      !loading &&
      incomingGeneratedMolecules !== lastPredictedMoleculesRef.current
    ) {
      lastPredictedMoleculesRef.current = incomingGeneratedMolecules;
      console.log('检测到分子数据，开始预测');
      runPrediction();
    }
  }, [incomingGeneratedMolecules, loading, runPrediction]);

  const excelInputRef = useRef<HTMLInputElement>(null);

  return (
    <div>
      <Modal visible={viewerVisible} onCancel={closeViewer} footer={null} width={520} title="分子 3D 视图">
        <div>
          <div style={{ maxHeight: 520, overflow: 'auto' }}>
          <p><b>类型:</b> {currentRecipe?.type ?? '-'}</p>
          <p><b>SMILES:</b> {currentRecipe?.smiles ?? '-'}</p>
          <div style={{ marginTop: 8 }}>
            <b>表格显示属性</b>
            <ul>
              {propertyFilters.map((pf) => {
                const raw = currentRecipe?.predicted?.[pf.key];
                const display = raw == null ? '-' : (typeof raw === 'number' && isFinite(raw) ? (Math.abs(raw) < 1e-3 ? raw.toExponential(3) : Number(raw).toFixed(4)) : String(raw));
                return <li key={pf.key}><b>{pf.label}:</b> {display}</li>;
              })}
            </ul>
          </div>
        </div>
        <MoleculeThreeViewer smilesList={viewerSmiles} width={480} height={320} background="#ffffff" />
        </div>
        
      </Modal>
      <Title level={4}>步骤4: 性质预测</Title>
      <Paragraph>
        使用知识和数据双驱动的性质预测模型对扩增后的配方进行高通量性质预测。
      </Paragraph>
      {loading ? (
        <div className="loading-container">
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text>正在进行高通量性质预测...</Text>
            <Progress
              percent={predictionProgress}
              status={predictionProgress >= 100 ? "success" : "active"}
              style={{ marginTop: 8 }}
            />
            <div style={{ marginTop: 8, fontSize: '12px', color: '#666' }}>
              {predictionProgress < 20 && "正在初始化预测模型..."}
              {predictionProgress >= 20 && predictionProgress < 40 && "正在加载分子结构数据..."}
              {predictionProgress >= 40 && predictionProgress < 60 && "正在进行分子性质计算..."}
              {predictionProgress >= 60 && predictionProgress < 80 && "正在筛选优质分子..."}
              {predictionProgress >= 80 && predictionProgress < 100 && "正在生成预测报告..."}
              {predictionProgress >= 100 && "预测完成！"}
            </div>
          </div>
        </div>
      ) : predictedData.length === 0 ? (
        <div>
          <Alert
            message="分子数据准备中"
            description="请点击下方按钮开始分子生成和性质预测。"
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
              开始性质预测
            </Button>
          </div>
        </div>
      ) : true ? (
        <div>
          <Alert
            message="分子性质预测完成"
            description={
              <div>
                <p>已成功完成分子生成和性质预测，筛选出性能最优的分子候选物。</p>
                <Text type="secondary">（基于AI模型生成的分子数据进行预测）</Text>
              </div>
            }
            type="success"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div>
              <Button type={libraryView === 'design' ? 'primary' : 'default'} onClick={() => setLibraryView('design')}>性质预测与配方设计</Button>
              <Button style={{ marginLeft: 8 }} type={libraryView === 'library' ? 'primary' : 'default'} onClick={() => setLibraryView('library')}>配方库</Button>
            </div>
          </div>

          {libraryView === 'design' ? (
            <div className={styles.MolecularSelection}>
              <div className={styles.filterPanel}>
                <div className={styles.filterTitle}>
                  <h3>性质筛选条件</h3>
                  <div className={styles.moduleBadge}>AI设计员</div>
                </div>
                <div className={styles.propertiesGrid}>
                  {propertyFilters.map((p) => (
                    <div key={p.key} className={styles.propertyItem}>
                      <div className={styles.propertyHeader}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span className={styles.propertyName}>{p.label}</span>
                          <span className={styles.propertyUnit}>{p.unit}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span className={styles.propertyTag}>数值</span>
                        </div>
                      </div>
                    
                      <div className={styles.rangeInputs}>
                        <InputNumber
                          placeholder="最小值"
                          value={filterValues[p.key]?.min ?? null}
                          onChange={(v) => handleFilterChange(p.key, 'min', v === undefined ? null : (v as number))}
                          min={p.minAllowed}
                          step={p.step}
                          precision={3}
                          style={{ borderRadius: '0' }}
                        />
                        <span>-</span>
                        <InputNumber
                          placeholder="最大值"
                          value={filterValues[p.key]?.max ?? null}
                          onChange={(v) => handleFilterChange(p.key, 'max', v === undefined ? null : (v as number))}
                          min={p.minAllowed}
                          step={p.step}
                          precision={3}
                          style={{ borderRadius: '0' }}
                        />
                      </div>
                    
                    </div>
                  ))}
                </div>
                <div className={styles.filterActions}>
                  <Button icon={<ExperimentOutlined />} onClick={handleResetFilters}> 重置条件</Button>
                  <Button icon={<ExperimentOutlined />} type="primary" onClick={handleApplyFilters}>应用筛选</Button>
                </div>
              </div>
              <div className={styles.tableContainer}>
                <Table
                  dataSource={(
                    sampleMolecules || []
                  ).filter((record: any) => {
                    // 检查所有已应用的过滤器
                    for (const pf of propertyFilters) {
                      const f = appliedFilters[pf.key];
                      if (!f) continue;
                      const min = f.min;
                      const max = f.max;
                      if (min == null && max == null) continue;

                      // 优先从 record.predicted 中取值
                      let raw = record.predicted?.[pf.key];
                      if (raw == null) raw = (record as any)[pf.key];
                      if (raw == null) return false; // 无该属性则过滤掉
                      const num = Number(raw);
                      if (!isFinite(num)) return false;
                      if (min != null && num < min) return false;
                      if (max != null && num > max) return false;
                    }
                    return true;
                  })}
                  columns={columns}
                  rowKey="id"
                  pagination={{ pageSize: 10, showSizeChanger: false, showQuickJumper: true, showTotal: (total) => `共 ${total} 条` }}
                  size="small"
                />
              </div>
              <div className={styles.formulaDesignPanel}>
                <div className={styles.moduleTitle}><h2>电解液配方设计</h2></div>
                <div className={styles.formulaSection}>
                  <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                    <div className={styles.formulaSectionTitle}><div className={styles.sectionIcon}>①</div><div className={styles.sectionTitleText}>添加配方分子（先选类型）</div></div>
                    {/* 配方库配方加载提示 */}
                    {selectedIngredients.length > 0 && (
                      <div style={{ margin: '8px 0', color: '#e67e22', fontWeight: 500 }}>
                        温馨提示：总添加剂的质量建议为配方总质量的 1% ~ 5%。
                      </div>
                    )}
                  </div>
                  
                  <div className={styles.ingredientControls}>
                    <div className={styles.ingredientInput} style={{ minWidth: 140 }}>
                      <label>分子类型</label>
                      <Select value={formulaType || undefined} onChange={(val) => setFormulaType(val)} options={[{ value: 'salt', label: '锂盐' }, { value: 'solvent', label: '溶剂' }, { value: 'additive', label: '添加剂' }]} />
                    </div>
                    <div className={styles.ingredientInput} style={{ flex: 1 }}>
                      <label>名称</label>
                      <Input value={ingredientName} onChange={(e) => setIngredientName(e.target.value)} placeholder="输入名称或从表中选择" />
                    </div>
                    <div className={styles.ingredientInput} style={{ width: 160 }}>
                      <label>质量 m (g)</label>
                      <InputNumber style={{ width: '100%' }} min={0} max={100} step={0.1} value={ingredientValue as number | null} onChange={(v) => setIngredientValue(v as number)} />
                    </div>
                    <div className={styles.ingredientInput} style={{ alignSelf: 'flex-end' }}>
                      <Button type="primary" onClick={addIngredient}>添加分子</Button>
                    </div>
                  </div>
                
                </div>
                <div style={{display:'flex',justifyContent:'space-between'}}>
                  <div className={styles.selectedIngredients}>
                    {selectedIngredients.length === 0 ? (
                      <div style={{ color: '#888' }}>尚未添加任何分子</div>
                    ) : (
                      selectedIngredients.map((ing, idx) => (
                        <div key={idx} className={styles.ingredientTag}>
                          <span className={styles.name}>{ing.name}</span>
                          <span className={styles.ratio}>{ing.type === 'salt' ? ing.concentration : `${ing.percent}`}g</span>
                          <button className={styles.removeTag} onClick={() => removeIngredient(idx)}>×</button>
                        </div>
                      ))
                    )}
                  </div>
                  <div className={styles.formulaActions}>
                    <Button onClick={clearFormula}>清空配方</Button>
                    <Button type="primary" onClick={saveRecipe}>保存配方</Button>
                  </div>
              </div>
              </div>
              <Space style={{ marginTop: 16 }}>
                <Button onClick={() => setCurrentStep && setCurrentStep(2)}>返回上一步</Button>
                <Button type="primary" onClick={handleGenerateFormula} loading={loading}>
                  生成最终配方
                </Button>
              </Space>
            </div>
          ) : (
            <div className={styles.RecipeLibrary}>
              {/* Excel 批量上传入口美化 */}
              <div style={{width:'100%', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 18, background: '#f7f3ff', borderRadius: 10, padding: '18px 24px', border: '1px solid #e5e1f5', boxShadow: '0 2px 8px #f0f0f0',justifyContent:'space-between' }}>
                <div style={{ flex: 'none', fontWeight: 600, fontSize: 16, color: '#7c3aed', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <ExperimentOutlined style={{ fontSize: 20 }} /> 批量导入配方
                </div>
                <div>
                   <span style={{ color: '#a78bfa', fontSize: 13, marginRight: 28 }}>支持 .xlsx/.xls，表头需包含 id/name/type/confidence/components 或分子1/比例1/SMILES1 等</span>
                  <label htmlFor="excel-upload" style={{ display: 'inline-block', cursor: 'pointer' }}>
                    <Button type="primary" onClick={() => excelInputRef.current?.click()} style={{  background: 'linear-gradient(90deg,#a18cd1 0%,#fbc2eb 100%)', border: 'none', fontWeight: 500 }}>
                      选择Excel文件
                    </Button>
                  </label>
                  <input
                    id="excel-upload"
                    type="file"
                    accept=".xlsx,.xls"
                    style={{ display: 'none' }}
                    ref={excelInputRef}
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      try {
                        const XLSX = await import('xlsx');
                        const reader = new FileReader();
                        reader.onload = (evt) => {
                          const data = evt.target?.result;
                          const workbook = XLSX.read(data, { type: 'array' });
                          const sheetName = workbook.SheetNames[0];
                          const sheet = workbook.Sheets[sheetName];
                          const json = XLSX.utils.sheet_to_json(sheet, { defval: '' });
                          const imported: any[] = [];
                          // 新增：支持“分子1/比例1/SMILES1、分子2/比例2/SMILES2...”多列方式，自动合并为一个配方
                          if (json.length > 0 && Object.keys(json[0]).some(k => /^分子\d+$/.test(k) || /^name\d+$/.test(k))) {
                            // 遍历每一行，合并所有分子列
                            json.forEach((row, rowIdx) => {
                              let components: any[] = [];
                              let i = 1;
                              while (row[`分子${i}`] || row[`name${i}`]) {
                                const name = row[`分子${i}`] || row[`name${i}`] || '';
                                const ratio = row[`比例${i}`] || row[`ratio${i}`] || '';
                                const smiles = row[`SMILES${i}`] || row[`smiles${i}`] || '';
                                if (name) components.push({ name, smiles, ratio });
                                i++;
                              }
                              const safeRow = row as Record<string, any>;
                              // 优先识别多种常见配方名表头
                              const nameField = safeRow.name || safeRow["配方名"] || safeRow["名称"] || safeRow["recipeName"] || safeRow["RecipeName"];
                              imported.push({
                                id: safeRow.id || `EXCEL${Date.now()}_${rowIdx+1}`,
                                name: nameField || `导入配方${rowIdx+1}`,
                                type: safeRow.type || '批量导入',
                                createdAt: safeRow.createdAt || new Date().toISOString(),
                                components
                              });
                            });
                          } 
                          setSavedRecipes(prev => [...imported, ...prev]);
                          message.success(`成功导入${imported.length}个配方`);
                        };
                        reader.readAsArrayBuffer(file);
                      } catch (err) {
                        message.error('解析Excel失败，请检查文件格式');
                      }
                    }}
                  />
                </div>
              </div>
              {savedRecipes.length === 0 ? (
                <Empty description="暂无已保存配方" />
              ) : (
                <div className={styles.formulaList} style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
                  {savedRecipes.map((recipe: any) => (
                    <div key={recipe.id} className={styles.formulaLibraryCard1}>
                      <div className={styles.formulaLibraryHeader}>
                        <div className={styles.formulaLibraryId}>{recipe.name}</div>
                      </div>
                      <hr className={styles.formulaLibraryDivider} />
                      <div className={styles.formulaLibraryComponents1}>
                        {recipe.components.map((comp: any, idx: number) => (
                          <div key={idx} className={styles.formulaLibraryComponent1} style={{display:'flex',justifyContent:'space-between'}}>
                            <span className={styles.formulaLibraryComponentName}>{comp.name}:</span>
                            <span className={styles.formulaLibraryComponentName}>{comp.smiles}:</span>
                            <span className={styles.formulaLibraryComponentRatio}>{comp.ratio}g</span>
                          </div>
                        ))}
                      </div>
                      <hr className={styles.formulaLibraryDivider} />
                      <div className={styles.formulaLibraryActions}>
                        <Button  size="small" className={styles.formulaLibraryBtn} type="primary" onClick={() => { loadRecipe(recipe); setLibraryView('design'); message.success('已加载配方到设计面板'); }}>采用此配方</Button>
                        <Button  size="small" className={styles.formulaLibraryBtn} danger onClick={() => deleteRecipe(recipe.id)}>删除</Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

         
        </div>
      ) : null}
    </div>
  );
};

export default Prediction;