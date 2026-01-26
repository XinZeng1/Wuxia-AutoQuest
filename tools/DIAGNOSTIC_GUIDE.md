# 怪物检测诊断指南

## 快速诊断

运行诊断工具来全面分析怪物检测问题：

```bash
python tools/diagnose_monster_detection.py
```

这个工具会：
1. 测试所有OpenCV匹配方法
2. 测试不同阈值下的匹配结果
3. 分析模板和截图图像质量
4. 生成可视化图像（标记所有可能的匹配位置）
5. 提供诊断报告和建议

## 诊断工具输出

### 1. 匹配方法测试结果

工具会测试所有OpenCV匹配方法，显示：
- 每种方法的最佳置信度
- 每种方法的匹配数量
- 推荐使用的方法

### 2. 阈值测试结果

显示不同阈值下的匹配数量，帮助确定合适的阈值。

### 3. 可视化图像

生成 `diagnostic_matches_visualization.png`，在截图上标记所有可能的匹配位置。

### 4. 诊断报告

根据测试结果提供：
- 问题诊断
- 改进建议
- 推荐的配置参数

## 根据诊断结果调整配置

### 如果最佳置信度低于阈值

1. **降低阈值**：编辑 `config/config.yaml`
   ```yaml
   recognition:
     template_match_threshold: 0.4  # 降低到诊断工具建议的值
   ```

2. **使用最佳匹配方法**：编辑 `config/config.yaml`
   ```yaml
   recognition:
     match_methods:
       - "TM_CCORR_NORMED"  # 使用诊断工具推荐的方法
   ```

3. **检查模板图像**：
   - 确保模板图像与实际游戏中的怪物图标一致
   - 模板应该清晰，背景尽量简单
   - 建议尺寸：50x50 到 100x100 像素

### 如果所有方法都无法匹配

1. **重新截图模板**：
   - 从游戏中重新截图一个更清晰的怪物图标
   - 确保模板包含完整的怪物特征

2. **尝试图像预处理**：编辑 `config/config.yaml`
   ```yaml
   recognition:
     preprocess:
       enabled: true
       enhance_contrast: true  # 尝试启用对比度增强
   ```

3. **使用多模板**：编辑 `config/config.yaml`
   ```yaml
   monster:
     templates:
       - "monster1.png"
       - "monster2.png"  # 添加多个模板
   ```

## 改进功能说明

### 1. 多匹配方法支持

系统现在会自动尝试多种OpenCV匹配方法：
- `TM_CCOEFF_NORMED` - 归一化相关系数（默认）
- `TM_CCORR_NORMED` - 归一化相关匹配
- `TM_SQDIFF_NORMED` - 归一化平方差

可以在配置中指定要使用的方法和优先级。

### 2. 自适应阈值

如果使用默认阈值无法匹配，系统会自动：
- 计算最高置信度
- 如果最高置信度接近阈值（80%以上），自动降低阈值重试
- 使用降低后的阈值进行匹配

### 3. 多模板支持

支持配置多个怪物模板：
- 系统会使用所有模板进行检测
- 合并所有模板的检测结果
- 自动去除重复的匹配

### 4. 图像预处理（可选）

可以启用图像预处理来提高匹配率：
- 对比度增强
- 边缘检测
- 二值化

注意：预处理可能提高也可能降低准确率，需要测试。

## 使用建议

1. **先运行诊断工具**：了解当前检测状态
2. **根据诊断结果调整配置**：使用工具推荐的方法和阈值
3. **测试改进效果**：运行 `python tools/test_monster_detection.py` 验证
4. **如果仍然失败**：尝试重新截图模板或启用预处理

## 模板质量分析

如果检测结果不理想（误报太多或检测不到），先分析模板质量：

```bash
python tools/analyze_template.py
```

这个工具会：
- 分析模板尺寸、亮度、对比度
- 检查边缘特征
- 提供改进建议

## 解决误报过多的问题

如果诊断工具显示匹配数量过多（如阈值0.6下有数万个匹配），说明存在大量误报。可以：

1. **提高阈值**：编辑 `config/config.yaml`
   ```yaml
   recognition:
     template_match_threshold: 0.85  # 提高到0.85或更高
   ```

2. **限制匹配数量**：编辑 `config/config.yaml`
   ```yaml
   recognition:
     max_matches: 5  # 只保留置信度最高的5个匹配
   ```

3. **改进模板图像**：
   - 重新截图，确保模板只包含怪物图标，背景尽量简单
   - 使用 `tools/analyze_template.py` 检查模板质量
   - 确保模板尺寸合适（50x50 到 150x150 像素）

4. **使用更严格的NMS**：编辑 `config/config.yaml`
   ```yaml
   recognition:
     nms_overlap_threshold: 0.2  # 降低重叠阈值，更严格地去除重复匹配
   ```

## 解决检测不到的问题

如果诊断工具显示所有方法都无法匹配：

1. **降低阈值**：编辑 `config/config.yaml`
   ```yaml
   recognition:
     template_match_threshold: 0.4  # 降低到0.4或更低
   ```

2. **检查模板图像**：
   - 确保模板与实际游戏中的怪物图标一致
   - 运行 `python tools/analyze_template.py` 检查模板质量
   - 尝试重新截图一个更清晰的模板

3. **启用预处理**：编辑 `config/config.yaml`
   ```yaml
   recognition:
     preprocess:
       enabled: true
       enhance_contrast: true
   ```

## 常见问题

**Q: 诊断工具显示所有方法都无法匹配？**
A: 可能是模板图像与实际怪物图标不匹配，建议重新截图模板。运行 `python tools/analyze_template.py` 检查模板质量。

**Q: 最佳置信度很低（<0.3）？**
A: 检查模板图像质量，确保模板清晰且与实际怪物一致。运行模板分析工具获取详细建议。

**Q: 检测到太多误匹配（数万个匹配）？**
A: 
1. 提高阈值到0.85或更高
2. 降低 `max_matches` 到5或更少
3. 重新截图模板，确保只包含怪物图标
4. 运行模板分析工具检查模板质量

**Q: 检测速度变慢？**
A: 在配置中只启用必要的匹配方法，或禁用预处理。降低 `max_matches` 也可以提高速度。
