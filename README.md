# “ACA筑韵古建”插件 for Blender

“ACA筑韵古建”插件（Ancient Chinese Architecture)是一个自动化生成清代北方官式建筑的工具。
- 依照《清工部·工程做法则例》，内置模数化权衡算法，生成原汁原味的古建筑。
- 既可以通过预制的模板样式库一键生成，也可以通过参数化设置打造你的个性化建筑。
- 运行在Blender建模软件中，跨平台支持Windows/MacOs/Linux，无需深入学习Blender，傻瓜化操作。
- 生成的建筑（包括贴图）可以导出FBX、GLB等格式，导入UE、D5、SU等软件中；

<img src="https://github.com/user-attachments/assets/375e96a9-02ae-425b-a984-de7202e7cc1a" alt="渲染效果图"/>

（上图用ACA筑韵古建插件生成模型，导入D5渲染器进行场景制作）

### 特点
1. 支持多种屋顶形态，包括：硬山、悬山、歇山、庑殿、盝顶。
    - 其中硬山、悬山、歇山支持有正脊的尖山、无正脊的卷棚两种形态。
2. 自动生成台基（踏跺）、柱网（大额枋/小额枋/平板枋）、装修（墙体/隔扇/槛窗）、清式斗科（一斗三升、斗口单昂、单翘单昂、斗口重昂，单翘重昂）
3. 自动生成屋顶的梁架、椽架、翼角、瓦面，内部结构完整。
4. 自动生成各个构件的UV和贴图，自带一套和玺彩画贴图，自带一套屋脊模型素材。

### 做法
本插件最大的特点是严格依据《清工部·工程则例》中的做法，通过python代码自动计算，生成的建筑精准的还原了清官式建筑的风韵。
1. 模数化：以斗口、柱径为基本模数因子，根据清官式建筑的权衡比例关系，计算古建筑中各个构件的尺寸，始终保持建筑各个部分的比例和谐。
2. 屋顶做法：参数化的举折、收山、推山做法，屋顶坡面可平缓、可陡峭。
3. 翼角做法：参数化的出冲、起翘，不同的参数可以形成不同的翼角风格。
4. 瓦面做法：自动生成曲面网格，逐一绑定筒瓦、板瓦、屋脊、脊兽等对象，瓦面流畅紧密。

---
### 详细文档
请参考：https://docs.qq.com/doc/DYXpwbUp1UWR0RXpu <br>
其中包含安装、联系方式等内容
