"""测试 NUT 客户端"""
import pytest
from services.nut_client import MockNutClient


class TestMockNutClient:
    """测试 MockNutClient"""
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self, mock_nut_client):
        """测试连接和断开"""
        await mock_nut_client.connect()
        assert mock_nut_client._connected is True
        
        await mock_nut_client.disconnect()
        assert mock_nut_client._connected is False
    
    @pytest.mark.asyncio
    async def test_list_vars_online(self, mock_nut_client):
        """测试在线状态的变量列表"""
        await mock_nut_client.connect()
        vars_dict = await mock_nut_client.list_vars()
        
        assert "ups.status" in vars_dict
        assert vars_dict["ups.status"] == "OL"
        assert "battery.charge" in vars_dict
        assert "battery.runtime" in vars_dict
        assert "ups.model" in vars_dict
    
    @pytest.mark.asyncio
    async def test_set_power_lost(self, mock_nut_client):
        """测试模拟断电"""
        await mock_nut_client.connect()
        
        mock_nut_client.set_power_lost()
        vars_dict = await mock_nut_client.list_vars()
        
        assert vars_dict["ups.status"] == "OB"
    
    @pytest.mark.asyncio
    async def test_set_power_restored(self, mock_nut_client):
        """测试模拟恢复供电"""
        await mock_nut_client.connect()
        
        mock_nut_client.set_power_lost()
        mock_nut_client.set_power_restored()
        vars_dict = await mock_nut_client.list_vars()
        
        assert vars_dict["ups.status"] == "OL"
        assert vars_dict["battery.charge"] == "100"
    
    @pytest.mark.asyncio
    async def test_set_low_battery(self, mock_nut_client):
        """测试模拟低电量"""
        await mock_nut_client.connect()
        
        mock_nut_client.set_low_battery(15)
        vars_dict = await mock_nut_client.list_vars()
        
        assert "LB" in vars_dict["ups.status"]
        assert vars_dict["battery.charge"] == "15"
    
    @pytest.mark.asyncio
    async def test_get_var(self, mock_nut_client):
        """测试获取单个变量"""
        await mock_nut_client.connect()
        
        status = await mock_nut_client.get_var("ups.status")
        assert status == "OL"
        
        charge = await mock_nut_client.get_var("battery.charge")
        assert charge == "100"
    
    @pytest.mark.asyncio
    async def test_list_ups(self, mock_nut_client):
        """测试列出 UPS 设备"""
        await mock_nut_client.connect()
        
        ups_list = await mock_nut_client.list_ups()
        assert len(ups_list) == 1
        assert ups_list[0]["name"] == "ups"
        assert "Mock UPS Device" in ups_list[0]["description"]
    
    @pytest.mark.asyncio
    async def test_set_battery_charge(self, mock_nut_client):
        """测试设置电池电量"""
        await mock_nut_client.connect()
        
        mock_nut_client.set_battery_charge(50)
        vars_dict = await mock_nut_client.list_vars()
        
        assert vars_dict["battery.charge"] == "50"
    
    @pytest.mark.asyncio
    async def test_list_rw_variables(self, mock_nut_client):
        """测试列出可写变量"""
        await mock_nut_client.connect()
        
        rw_vars = await mock_nut_client.list_rw()
        
        # 检查返回的数据结构
        assert isinstance(rw_vars, dict)
        
        # 检查是否包含预期的可写变量
        assert "input.transfer.high" in rw_vars
        assert "input.transfer.low" in rw_vars
        assert "input.sensitivity" in rw_vars
        assert "ups.delay.shutdown" in rw_vars
        
        # 检查变量元数据
        assert rw_vars["input.transfer.high"]["writable"] is True
        assert "value" in rw_vars["input.transfer.high"]
    
    @pytest.mark.asyncio
    async def test_set_var_voltage_threshold(self, mock_nut_client):
        """测试设置电压阈值"""
        await mock_nut_client.connect()
        
        # 设置高压阈值
        success = await mock_nut_client.set_var("input.transfer.high", "260")
        assert success is True
        
        # 验证值已更新
        value = await mock_nut_client.get_var("input.transfer.high")
        assert value == "260"
    
    @pytest.mark.asyncio
    async def test_set_var_sensitivity(self, mock_nut_client):
        """测试设置输入灵敏度"""
        await mock_nut_client.connect()
        
        # 设置为 medium
        success = await mock_nut_client.set_var("input.sensitivity", "medium")
        assert success is True
        
        # 验证值已更新
        value = await mock_nut_client.get_var("input.sensitivity")
        assert value == "medium"
        
        # 设置为 high
        success = await mock_nut_client.set_var("input.sensitivity", "high")
        assert success is True
        
        value = await mock_nut_client.get_var("input.sensitivity")
        assert value == "high"
    
    @pytest.mark.asyncio
    async def test_set_var_shutdown_delay(self, mock_nut_client):
        """测试设置关机延迟"""
        await mock_nut_client.connect()
        
        # 设置延迟为 30 秒
        success = await mock_nut_client.set_var("ups.delay.shutdown", "30")
        assert success is True
        
        # 验证值已更新
        value = await mock_nut_client.get_var("ups.delay.shutdown")
        assert value == "30"
    
    @pytest.mark.asyncio
    async def test_set_var_updates_mock_data(self, mock_nut_client):
        """测试 set_var 同时更新 mock_data"""
        await mock_nut_client.connect()
        
        # 设置可写变量
        await mock_nut_client.set_var("input.transfer.low", "150")
        
        # 检查 list_vars 也能获取到更新后的值
        vars_dict = await mock_nut_client.list_vars()
        assert vars_dict["input.transfer.low"] == "150"
