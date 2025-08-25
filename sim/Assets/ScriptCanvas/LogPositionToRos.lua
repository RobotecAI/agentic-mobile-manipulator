local PrintPosition = 
{
    Properties = {}
}

function PrintPosition:OnActivate()
    -- Cache entityId
    self.entityId = self.entityId or self:GetEntityId()

    -- Connect to TickBus
    self.tickBusHandler = TickBus.Connect(self)
end

function PrintPosition:OnDeactivate()
    if self.tickBusHandler then
        self.tickBusHandler:Disconnect()
        self.tickBusHandler = nil
    end
end

function PrintPosition:OnTick(deltaTime, timePoint)
    local position = TransformBus.Event.GetWorldTranslation(self.entityId)
    local rotation = TransformBus.Event.GetWorldRotationQuaternion(self.entityId)
    local name = GameEntityContextRequestBus.Broadcast.GetEntityName(self.entityId)
   	local msg = string.format("%s,%s,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f",
        name, tostring(self.entityId),
        position.x, position.y, position.z, rotation.x, rotation.y, rotation.z, rotation.w)
    PublisherRequestBus.Broadcast.PublishStdMsgString("sim/reported_points",msg)

    self.tickBusHandler:Disconnect()
    self.tickBusHandler = nil
end

return PrintPosition